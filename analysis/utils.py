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
            p = morph.parse(token)[0]
            if len(p.normal_form) < word_len_threshold:
                continue
            
            # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
            if any(tag in str(p.tag) for tag in ['LATN', 'PNCT', 'NUMB', 'UNKN']):
                continue
            # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
            if str(p.tag.POS) not in filter:
                otput_data += " " +  str(p.normal_form)  
        
    return otput_data

def process_code(text):
    otput_data = list()

    text = re.sub('<[^<]+?>', ' ', text, flags=re.DOTALL) 
    text = re.sub('(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9]+)', ' ', text, flags=re.DOTALL)             
    text = re.sub('(https|http)?:\/\/.*', '', text)
    text = text.lower()

    sent_text = nltk.sent_tokenize(text)
    for sentence in sent_text:
        tokenized_text = nltk.word_tokenize(sentence)
        for token in tokenized_text:
            if langs.is_programming_word(token):
                otput_data.append(token)

    return otput_data