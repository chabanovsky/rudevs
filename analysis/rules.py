import nltk
import csv
import re
import collections
from analysis.utils import filter_noise, morph

class RuleAnalyser():
    vocabualary = dict()
    common_words = dict()
    rules = dict()

    def __init__(self, vocabualary=None, filename="questions.csv"):
        self.filename = filename
        if vocabualary is None:
            self.process(self.build_vocabualary)
        else:
            self.vocabualary = vocabualary
            
        self.common_words = collections.Counter(self.vocabualary).most_common(len(self.vocabualary) // 100)
        self.process(self.build_rules)

    def process(self, action_func):
        with open(self.filename, 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                _, _, _, _, body, _ = row
                action_func(filter_noise(body))

    def build_vocabualary(self, text):
        sent_text = nltk.sent_tokenize(text)
        for sentence in sent_text:
            tokenized_text = nltk.word_tokenize(sentence)
            for token in tokenized_text:
                p = morph.parse(token)[0]

                if any(tag in str(p.tag) for tag in ['LATN', 'PNCT', 'NUMB', 'UNKN']):
                    continue
            
                if str(p.tag.POS) not in ['NPRO', 'PRED', 'PREP', 'CONJ', 'PRCL', 'INTJ', 'NUMB']:
                    if self.vocabualary.get(p.normal_form, None) is None:
                        self.vocabualary[p.normal_form] = 1 
                    else: 
                        self.vocabualary[p.normal_form] += 1        
        
    def build_rules(self, text):
        sent_text = nltk.sent_tokenize(text)
        for sentence in sent_text:
            tokenized_text = nltk.word_tokenize(sentence)
            index = 0
            for token in tokenized_text:
                p = morph.parse(token)[0]

                if str(p.normal_form) not in self.common_words:
                    continue
                
                sub_text = tokenized_text[index+1:]
                rule = list()

                for sub_token in sub_text:
                    sub_p = morph.parse(sub_token)[0]
                    if any(tag in str(sub_p.tag) for tag in ['LATN', 'PNCT', 'NUMB', 'UNKN']):
                        continue
                
                    if str(sub_p.tag.POS) not in ['NPRO', 'PRED', 'PREP', 'CONJ', 'PRCL', 'INTJ', 'NUMB']:
                        rule.append(sub_p.normal_form)

                if self.rules.get(p.normal_form, None) is None:
                    self.rules[p.normal_form] = list()
                
                self.rules[p.normal_form].append(rule)

                index +=1
         
        
