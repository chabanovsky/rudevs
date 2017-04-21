import nltk
import csv
import re
import sys
import collections
import tensorflow as tf
from sqlalchemy import desc

from analysis.utils import process_text, morph
from meta import db_session
from models import DBStaticAssessment

class StaticAssessment():
    question_count              = 0
    mimimum_question_length     = sys.maxsize
    maximum_question_length     = 0
    mimimum_question_word_count = sys.maxsize
    maximum_question_word_count = 0

    divider_coefficient = 20

    def __init__(self, filename="questions.csv"):
        self.filename = filename

    def update(self):
        with open(self.filename, 'rt', encoding="utf8") as csvfile:
            question_lengths = list()
            vocaboalary_sizes = list()
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                _, _, _, _, body, _ = row
                self.question_count +=1
                question_lengths.append(len(body))
                # All the paramentors should be the same as they are when we process real messages.
                vocaboalary = process_text(body, True, 2)
                vocaboalary = tf.compat.as_str(vocaboalary).split()
                vocaboalary_sizes.append(len(vocaboalary))

            question_lengths = sorted(question_lengths)
            question_lengths_length = len(question_lengths)
            vocaboalary_sizes = sorted(vocaboalary_sizes)
            vocaboalary_sizes_length = len(vocaboalary_sizes)
            
        self.mimimum_question_length = question_lengths[question_lengths_length // self.divider_coefficient]
        self.maximum_question_length = question_lengths[question_lengths_length // self.divider_coefficient * (self.divider_coefficient - 1)]
        self.mimimum_question_word_count = vocaboalary_sizes[vocaboalary_sizes_length // self.divider_coefficient]
        self.maximum_question_word_count = vocaboalary_sizes[vocaboalary_sizes_length // self.divider_coefficient  * (self.divider_coefficient - 1)]
        
        static_assessment = DBStaticAssessment(self.question_count,
                self.mimimum_question_length,
                self.maximum_question_length,
                self.mimimum_question_word_count,
                self.maximum_question_word_count)

        session = db_session()        
        session.add(static_assessment)
        session.commit()
        session.close()

    def load(self, id=None):
        session = db_session()
        query = session.query(DBStaticAssessment.id, 
                DBStaticAssessment.question_count,
                DBStaticAssessment.mimimum_question_length,
                DBStaticAssessment.maximum_question_length,
                DBStaticAssessment.mimimum_question_word_count,
                DBStaticAssessment.maximum_question_word_count)
        if id is None:
            query = query.order_by(desc(DBStaticAssessment.id))
        else:
            query = query.filter(DBStaticAssessment.id==id)
        db_item = query.first()

        self.question_count = int(db_item.question_count)
        self.mimimum_question_length = int(db_item.mimimum_question_length)
        self.maximum_question_length = int(db_item.maximum_question_length)
        self.mimimum_question_word_count = int(db_item.mimimum_question_word_count)
        self.maximum_question_word_count = int(db_item.maximum_question_word_count)


    def __str__(self):
        return "question_count: " + str(self.question_count) + \
         ", mimimum_question_length: " + str(self.mimimum_question_length) + \
         ", maximum_question_length: " + str(self.maximum_question_length) + \
         ", mimimum_question_word_count: " + str(self.mimimum_question_word_count) + \
         ", maximum_question_word_count: " + str(self.maximum_question_word_count) 
         
