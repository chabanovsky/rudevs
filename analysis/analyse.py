# encoding:utf-8
"""Basic word2vec example."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import csv
import collections
import math
import os
import random
import zipfile
import re

import numpy as np
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf

from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

from sqlalchemy import desc, and_, or_, asc
from sqlalchemy.sql import func, literal_column, update
from sqlalchemy.dialects.postgresql import aggregate_order_by

from models import SkippGramVocabulary, VocabularyQueston, Statement, TelegramTextMessage, NegativeExample, TelegramChannel
from meta import db_session, MINIMIM_QUESTION_LENGHT
from analysis.word2vec_model import Word2VecModel
from analysis.rules import RuleAnalyser
from analysis.question_words import QuestionWords
from analysis.utils import filter_noise, process_text, process_code, print_progress_bar
from analysis.static_assessment import StaticAssessment
from analysis.negative_examples import BigQuestion
from analysis.tf_idf import TfIdfModel, TfIdfConvModel

class QuestionAnalyser():
    question_words = QuestionWords()
    selfdict = dict()
     # if a phrase has a keyword and context_word_threshold 
     # words around the keyword we think that this is a simmilar question
    context_word_threshold = 2

    def __init__(self):
        self.model = Word2VecModel()    
        self.model.prepare_most_common_words()
        self.static_assessment = StaticAssessment()
        self.static_assessment.load()

    def validate(self, question_str):
        text = question_str.lower()
        text_length = len(text)

        if text_length < self.static_assessment.mimimum_question_length or \
                text_length > self.static_assessment.maximum_question_length:
            print ("[not valid: text_length(", text_length, "), min(", 
                    self.static_assessment.mimimum_question_length, "), max(",
                    self.static_assessment.maximum_question_length,")]")   
            return False

        filtered_vocabualary = process_text(text, extended_filter=True, word_len_threshold=2)
        filtered_vocabualary = tf.compat.as_str(filtered_vocabualary).split()
        filtered_vocabualary_size = len(filtered_vocabualary)

        if filtered_vocabualary_size < self.static_assessment.mimimum_question_word_count or \
                filtered_vocabualary_size > self.static_assessment.maximum_question_word_count:
            print ("[not valid: filtered_vocabualary_size (", 
                    filtered_vocabualary_size, "), min (", 
                    self.static_assessment.mimimum_question_word_count, "), max (", 
                    self.static_assessment.maximum_question_word_count, ")]")            
            return False

        if not self.has_question_words(filtered_vocabualary):
            print ("[not valid: no question words]")            
            return False

        keywords = list()
        keywords_count = 0

        for index, filtered_word in enumerate(filtered_vocabualary):
            nearest = self.model.most_common_words.get(filtered_word, None)
            if nearest is not None:
                keywords_count += 1
                min_index = max(0, index-self.model.skip_window)
                max_index = min(filtered_vocabualary_size-1, index+self.model.skip_window)
                sub_array = filtered_vocabualary[min_index:max_index]
                inter_sub_array = set(sub_array).intersection(nearest)
                keywords.extend(inter_sub_array)
        
        if (keywords_count >= filtered_vocabualary_size // 3) and (len(keywords) >= keywords_count//self.context_word_threshold):
            print (question_str.strip(), " [valid: most frequent words (kc: ", keywords_count, ", len: ", len(keywords) ,"/", filtered_vocabualary_size // 3 , ")] total common: ", len(self.model.most_common_words))            
            return True

        print ("[Not valid/Not defined] keywords_count: ", keywords_count, ", filtered_vocabualary_size // 3: ", filtered_vocabualary_size // 3, ", len(keywords): ", len(keywords))
        return False

    def has_question_words(self, vocabualary):
        for word in vocabualary:
            if self.question_words.is_question_word(word):
                return True
        return False

def update_stored_data():
    model = Word2VecModel()
    model.update_train_data()
    static_assessment = StaticAssessment()
    static_assessment.update()
    
def do_analyse():
    model = Word2VecModel()
    model.train()
    model.validate_examples()
    
def do_validate():
    model = Word2VecModel()
    model.validate_examples()

def load_questions(check_existence=True):
    question_words_checker = QuestionWords()
    session = db_session()

    with open("questions.csv", 'rt', encoding="utf8") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        for row in csv_reader:
            so_id, score, answer_count, title, body, tags = row
            length = len(body)
            processed_body = tf.compat.as_str(process_text(body, True, 2))
            code_words = tf.compat.as_str(process_code(body))
            filtered_vocabualary = processed_body.split()
            tags = tags.replace('|', " ")
            word_count = len(filtered_vocabualary)
            question_words = ""
            for word in filtered_vocabualary:
                if question_words_checker.is_question_word(word):
                    question_words += " " + word
            VocabularyQueston.update_or_create(session,
                so_id, 
                body, 
                title, 
                tags, 
                score, 
                length, 
                word_count, 
                question_words, 
                processed_body,
                code_words, 
                False)

        session.commit()
        session.close()

def do_auto_review():
    session = db_session()

    subquery = session.query(Statement.id.label('statement_id'), func.length(func.string_agg(TelegramTextMessage.message, 
                aggregate_order_by(literal_column("'. '"), 
                        TelegramTextMessage.created))).label('agg_message')).\
            filter(Statement.reviewed==False).\
            filter(and_(TelegramTextMessage.channel_id==Statement.channel_id, TelegramTextMessage.user_id==Statement.user_id)).\
            filter(TelegramTextMessage.message_id.between(Statement.first_msg_id, Statement.last_msg_id)).\
            group_by(Statement.id).\
            subquery()

    query = session.query(subquery.c.statement_id).filter(subquery.c.agg_message<MINIMIM_QUESTION_LENGHT).subquery()
    stmt = update(Statement).where(Statement.id.in_(query)).values(reviewed=True, is_question=False, false_assumption=False)
    
    session.execute(stmt)
    session.commit()
    session.close()

def genereate_negative_examples(check_existence=True):
    question_words_checker = QuestionWords()
    session = db_session()

    query = session.query(Statement.id.label('statement_id'), func.string_agg(TelegramTextMessage.message, 
                aggregate_order_by(literal_column("'. '"), 
                        TelegramTextMessage.created)).label('agg_message')).\
            filter(Statement.reviewed==True).\
            filter(Statement.is_question==Statement.false_assumption).\
            filter(and_(TelegramTextMessage.channel_id==Statement.channel_id, TelegramTextMessage.user_id==Statement.user_id)).\
            filter(TelegramTextMessage.message_id.between(Statement.first_msg_id, Statement.last_msg_id)).\
            group_by(Statement.id).\
            subquery()

    query = session.query(query.c.statement_id, query.c.agg_message, func.length(query.c.agg_message).label('len'), TelegramChannel.tags.label('tags')).\
            outerjoin(Statement, Statement.id==query.c.statement_id).\
            outerjoin(TelegramChannel, TelegramChannel.channel_id==Statement.channel_id).distinct()

    session.close()
    session = db_session()

    for item in query.all(): 
        filtered_words = tf.compat.as_str(process_text(item.agg_message, True, 2))   
        filtered_vocabualary = filtered_words.split()   
        word_count = len(filtered_vocabualary)
        code_words = tf.compat.as_str(process_code(item.agg_message))
        
        question_words = ""
        for word in filtered_vocabualary:
            if question_words_checker.is_question_word(word):
                question_words += " " + word

        if check_existence:
            voc_qstn = NegativeExample.query.filter_by(statement_id=item.statement_id).first()
            if voc_qstn is not None:
                update_query = NegativeExample.__table__.update().values(
                        body=item.agg_message, 
                        tags=item.tags,
                        length=item.len,
                        word_count=word_count,
                        code_words=code_words,
                        filtered_words=filtered_words,
                        question_words=question_words).\
                    where(NegativeExample.statement_id==item.statement_id)
                session.execute(update_query)
                continue

        neg = NegativeExample(item.agg_message, 
                item.tags, 
                item.len,
                word_count,
                question_words,
                filtered_words, 
                code_words, 
                item.statement_id)
        session.add(neg)

    session.commit()
    session.close()

def do_print_most_common_words():
    model = Word2VecModel()
    model.upload_dataset()
    voc_size = len(model.count)
    most_common_words = model.count[:(voc_size//100)]
    print ("Total vocabulary size: ", voc_size)
    for item in most_common_words:
        print (item)

def test_analyser():
    analyser = QuestionAnalyser()
    with open("questions.csv", 'rt', encoding="utf8") as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=',')
        counter = 0
        valid = 0
        for row in csv_reader:
            _, _, _, _, body, _ = row
            if analyser.validate(body):
                valid += 1
            if counter == 10:
                break
            counter +=1 
        print ("Total valid: ", valid)

def upload_big_questions():
    big = BigQuestion()
    big.process()

def train_tfidf():
    model = TfIdfModel()
    model.train()
    model.validate_model()

def validate_tfidf():   
    model = TfIdfModel()
    model.restore_last() 
    model.validate_model()

def train_tfidf_conv():
    model = TfIdfConvModel()
    model.train()
    model.validate_model()    
    model.validate_get_class()

def validate_tfidf_conv():   
    model = TfIdfConvModel()
    model.restore_last() 
    model.validate_get_class()


def test_nltk():
    model = Word2VecModel()    
    model.restore_last()
    vocabualary = dict()
    for word, count in model.count:
        vocabualary[word] = count

    analyser = RuleAnalyser(vocabualary)
    print (analyser.common_words)
    print ("-------------------")
    print (analyser.rules)
    