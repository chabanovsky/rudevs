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

from sqlalchemy import desc, and_, asc
from sqlalchemy.sql import func, literal_column, update
from sqlalchemy.dialects.postgresql import aggregate_order_by

from models import SkippGramVocabulary, VocabularyQueston, Statement, TelegramTextMessage, NegativeExample
from meta import db_session, MINIMIM_QUESTION_LENGHT
from analysis.word2vec_model import Word2VecModel
from analysis.rules import RuleAnalyser
from analysis.question_words import QuestionWords
from analysis.utils import filter_noise, process_text, process_code, print_progress_bar
from analysis.static_assessment import StaticAssessment

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
            print ("[not valid: text_length(", text_length, ")]")   
            return False

        filtered_vocabualary = process_text(text, extended_filter=True, word_len_threshold=2)
        filtered_vocabualary = tf.compat.as_str(filtered_vocabualary).split()
        filtered_vocabualary_size = len(filtered_vocabualary)

        if filtered_vocabualary_size < self.static_assessment.mimimum_question_word_count or \
                filtered_vocabualary_size > self.static_assessment.maximum_question_word_count:
            print ("[not valid: filtered_vocabualary_size (", filtered_vocabualary_size, ")]")            
            return False

        if not self.has_question_words(filtered_vocabualary):
            print ("[not valid: no question words]")            
            return False

        keywords = list()

        for index, filtered_word in enumerate(filtered_vocabualary):
            nearest = self.model.most_common_words.get(filtered_word, None)
            if nearest is not None:
                sub_array = filtered_word[min(0, index-self.model.skip_window):min(filtered_vocabualary_size-1, index+self.model.skip_window)]
                items_found = len(set(sub_array).intersection(nearest))
                if items_found >= self.context_word_threshold:
                    keywords.append(filtered_word)
                
                keywords.append(nearest)
        
        if len(keywords) >= filtered_vocabualary_size // 3:
            print (question_str.strip(), " [valid: most frequent words (", len(keywords) ,"/", filtered_vocabualary_size // 3 , ")] total common: ", len(self.model.most_common_words))            
            return True

        print ("[Not valid/Not defined]")
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

def load_questions(check_existence=False):
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
            
            if check_existence:
                voc_qstn = VocabularyQueston.query.filter_by(so_id=so_id).first()
                if voc_qstn is not None:
                    update_query = VocabularyQueston.__table__.update().values(
                            body=body, 
                            title=title,
                            tags=tags,
                            score=score,
                            length=length,
                            word_count=word_count,
                            code_words=code_words,
                            question_words=question_words).\
                        where(VocabularyQueston.so_id==so_id)
                    session.execute(update_query)
                    continue

            voc_qstn = VocabularyQueston(
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
                True)

            session.add(voc_qstn)

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
            if counter == 1000:
                break
            counter +=1 
        print ("Total valid: ", valid)

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
    