# encoding:utf-8
from __future__ import print_function

import re
import nltk
import pymorphy2
from analysis.langs import Langs

morph = pymorphy2.MorphAnalyzer()
langs = Langs()

def filter_noise(text):
    text = re.sub('<pre>.*?</pre>',' ', text, flags=re.DOTALL)
    text = re.sub('<code>.*?</code>',' ', text, flags=re.DOTALL)
    text = re.sub('<[^<]+?>', ' ', text, flags=re.DOTALL) 
    text = re.sub('(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)', ' ', text, flags=re.DOTALL)             
    text = re.sub('(https|http)?:\/\/.*', '', text)
    return text

def process_text(text, extended_filter=False, word_len_threshold=3):
    global morph

    def process(filter, token, word_len_threshold):
        global morph

        p = morph.parse(token)[0]
        if len(p.normal_form) < word_len_threshold:
            return None
        
        # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
        if any(tag in str(p.tag) for tag in ['LATN', 'PNCT', 'NUMB', 'UNKN']):
            return None
        # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
        if str(p.tag.POS) not in filter:
            return  str(p.normal_form)  

    otput_data = ""
    if extended_filter:
        filter = ['PREP']
    else:    
        filter = ['NPRO', 'PREP', 'PRED', 'CONJ', 'PRCL', 'INTJ']

    text = filter_noise(text)
    text = text.lower()

    sent_text = nltk.sent_tokenize(text)
    for sentence in sent_text:
        tokenized_text = nltk.word_tokenize(sentence)
        for token in tokenized_text:
            
            token = token.replace('.', ' ')
            token = token.replace('-', ' ')
            token = token.replace('/', ' ')

            for sub_token in token.split():
                processed = process(filter, sub_token, word_len_threshold)
                if processed is not None:
                    otput_data += " " + processed
        
    return otput_data

def process_code(text):
    otput_data = ""

    text = re.sub('<[^<]+?>', ' ', text, flags=re.DOTALL) 
    text = re.sub('(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)', ' ', text, flags=re.DOTALL)             
    text = re.sub('(https|http)?:\/\/.*', '', text)
    text = text.lower()
    
    sent_text = nltk.sent_tokenize(text)
    for sentence in sent_text:
        tokenized_text = nltk.word_tokenize(sentence)
        for token in tokenized_text:
            if langs.is_programming_word(token):
                otput_data += " " + token

    return otput_data

# Print iterations progress: http://stackoverflow.com/a/34325723/564240
def print_progress_bar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = u'█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print ('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total: 
        print ()

def print_association_setting(association_list):
    for item in association_list:
        s = str(item["soen"]) + "=" + str(item["soint"])
        print (s, end=',')
    
    print ()