import requests
import tensorflow as tf
from bs4 import BeautifulSoup
import time
import re

from models import SourceData
from analysis.utils import process_text, process_code
from analysis.question_words import QuestionWords

class BigQuestion():
    # each page has 20 questions
    number_of_page_to_upload = 2000 
    domain = "http://www.bolshoyvopros.ru"
    base_url = "http://www.bolshoyvopros.ru/questions/actual/cat10"
    extension = ".html"
    paganator = "_p%d"
    question_words_checker = QuestionWords()

    def __init__(self):
        pass

    def process(self):
        for index in range(self.number_of_page_to_upload):
            self.process_page(self.number_of_page_to_upload - index)
            time.sleep(30)

    def process_page(self, page_number):
        url = self.base_url + (self.paganator % page_number) + self.extension
        response = requests.get(url)
        soup = BeautifulSoup(response.text)
        links = soup.find_all("a", class_="question_title")
        for link in links:
            if link.get('href', None) is None:
                continue
            self.process_question(self.domain + link['href'])
            time.sleep(5)

    def process_question(self, question_url):
        response = requests.get(question_url)
        soup = BeautifulSoup(response.text)
        question_id = int(re.search('(\d+)', question_url).group(0))
        h1 = soup.find('h1')
        if h1 is None:
            return
        title = h1.getText()
        message = soup.find(class_='message')
        if message is None:
            return
        question = message.getText().replace('+', "").strip()
        if len(question) == 0:
            question = title
        score = soup.find(class_='votes')
        if score is None:
            score = 0
        else:
            score = int(score.getText())

        tags = list()
        for item in soup.find_all(class_='tags'):
            for sub_item in item.find_all('a'):
                tags.append(sub_item.getText())
        tags = ' '.join(tags)

        print ("id: ", question_id, ", title: ", title, ", score: ", score, ", tags: ", tags)
        print ("question: ", question)

        length = len(question)
        processed_question = tf.compat.as_str(process_text(question, True, 2))
        code_words = tf.compat.as_str(process_code(question))
        filtered_vocabualary = processed_question.split()

        word_count = len(filtered_vocabualary)
        question_words = ""
        for word in filtered_vocabualary:
            if self.question_words_checker.is_question_word(word):
                question_words += " " + word

        SourceData.update_or_create(None,
                question_id,
                SourceData.source_type_so_bq_question,
                question, 
                title, 
                tags, 
                score, 
                length, 
                word_count, 
                question_words, 
                processed_question,
                code_words, 
                True)

        
