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

from models import SourceData, Statement, TelegramTextMessage, TelegramChannel
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

        return False

    def has_question_words(self, vocabualary):
        for word in vocabualary:
            if self.question_words.is_question_word(word):
                return True
        return False

def load_source_data():
    SourceData.load_all()                 

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
    # TODO: Change to SourceDataWrapper
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
    