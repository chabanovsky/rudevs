# encoding:utf-8
import pymorphy2

class QuestionWords():
    
    def __init__(self):
        morph = pymorphy2.MorphAnalyzer()
        words = dict()
        for word in self.question_words():
            word = word.lower()
            p = morph.parse(word)[0]
            if words.get(p.normal_form, None) is None:
                words[p.normal_form] = 1
            else:
                words[p.normal_form] += 1

        self.words = words

    def is_question_word(self, test_word):
        return self.words.get(test_word, None) is not None        

    @staticmethod
    def question_words():
        return {
            u"ась",
            u"аюшки",
            u"где",
            u"докуда",
            u"зачем",
            u"как",
            u"как-то",
            u"каков",
            u"какой",
            u"куда",
            u"кто",
            u"кем",
            u"кому",
            u"который",
            u"может",
            u"насколько",
            u"отколь",
            u"откуда",
            u"откудова",
            u"отчего",
            u"почему",
            u"подскажите",
            u"сколько",
            u"или",
            u"ли",
            u"неужели",
            u"разве",
            u"ужели",
            u"ужель",
            u"чей",
            u"что",
            u"какой-либо"
        }
