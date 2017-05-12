import datetime
import collections
import numpy as np

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, ColumnDefault
from sqlalchemy import and_, or_, desc
from sqlalchemy.sql import func, literal_column
from sqlalchemy.dialects.postgresql import aggregate_order_by

from meta import app as application, db, db_session

class Statement(db.Model):
    __tablename__ = 'statement'

    id              = db.Column(db.Integer, primary_key=True)
    channel_id      = db.Column(db.BigInteger)
    user_id         = db.Column(db.BigInteger)
    first_msg_id    = db.Column(db.BigInteger)
    last_msg_id     = db.Column(db.BigInteger)
    text            = db.Column(db.String)
    # first added msg creation time
    created         = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    # last added msg creation time
    updated         = db.Column(db.DateTime, nullable=False, default=datetime.datetime.now)
    was_processed   = db.Column(db.Boolean, default=False)
    is_question     = db.Column(db.Boolean, default=False)
    false_assumption= db.Column(db.Boolean, default=False)
    reviewed        = db.Column(db.Boolean, default=False)

    def __init__(self, channel_id, 
            user_id, 
            first_msg_id,
            created=datetime.datetime.now(),
            is_question=False,
            was_processed=False,
            reviewed=False):
        self.channel_id     = channel_id
        self.user_id        = user_id
        self.first_msg_id   = first_msg_id
        self.last_msg_id    = first_msg_id
        self.created        = created
        self.updated        = created
        self.is_question    = is_question 
        self.was_processed  = was_processed
        self.reviewed       = reviewed

    def __repr__(self):
        return '<Stmnt %r>' % str(self.id)

class TelegramChannel(db.Model):
    __tablename__ = 'telegram_channel'

    id          = db.Column(db.Integer, primary_key=True)
    channel_id  = db.Column(db.BigInteger)
    title       = db.Column(db.String)
    username    = db.Column(db.String)
    tags        = db.Column(db.String)
    access_hash = db.Column(db.BigInteger)

    def __init__(self, channel_id, 
            title, 
            username, 
            access_hash):
        self.channel_id = channel_id
        self.title = title
        self.username = username
        self.access_hash = access_hash

    def __repr__(self):
        return '<TChannel %r>' % str(self.id)

class TelegramTextMessage(db.Model):
    __tablename__ = 'telegram_text_message'

    id              = db.Column(db.Integer, primary_key=True)
    message_id      = db.Column(db.BigInteger)
    message         = db.Column(db.String)
    created         = db.Column(db.DateTime, default=datetime.datetime.now)
    channel_id      = Column(db.BigInteger)
    user_id         = Column(db.BigInteger)
    reply_to_id     = db.Column(db.BigInteger)

    def __init__(self, message_id, 
            message, 
            channel_id, 
            user_id, 
            reply_to_id, 
            created=datetime.datetime.now()):
        self.message_id     = message_id
        self.message        = message
        self.channel_id     = channel_id
        self.user_id        = user_id
        self.reply_to_id    = reply_to_id
        self.created        = created

    def __repr__(self):
        return '<TTxtMsg %r>' % str(self.id)

class TelegramUser(db.Model):
    __tablename__ = 'telegram_user'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.BigInteger)
    first_name  = db.Column(db.String)
    last_name   = db.Column(db.String)
    username    = db.Column(db.String)

    def __init__(self, user_id,
            first_name, 
            last_name, 
            username):
        self.user_id    = user_id
        self.first_name = first_name
        self.last_name  = last_name
        self.username   = username

    def __repr__(self):
        return '<TUser %r>' % str(self.id)


class SkippGramVocabulary(db.Model):
    __tablename__ = 'skipp_gram_vocabulary'

    id          = db.Column(db.Integer, primary_key=True)
    vocabulary  = db.Column(db.String)

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    def __repr__(self):
        return '<SGVoc %r>' % str(self.id)

class DBStaticAssessment(db.Model):
    __tablename__ = 'static_assessment'

    id                          = db.Column(db.Integer, primary_key=True)
    question_count              = db.Column(db.Integer)
    mimimum_question_length     = db.Column(db.Integer)
    maximum_question_length     = db.Column(db.Integer)
    mimimum_question_word_count = db.Column(db.Integer)
    maximum_question_word_count = db.Column(db.Integer)

    def __init__(self, question_count, 
            mimimum_question_length, 
            maximum_question_length, 
            mimimum_question_word_count, 
            maximum_question_word_count):
        self.question_count = question_count
        self.mimimum_question_length = mimimum_question_length
        self.maximum_question_length = maximum_question_length
        self.mimimum_question_word_count = mimimum_question_word_count
        self.maximum_question_word_count = maximum_question_word_count

    def __repr__(self):
        return '<DBSA %r>' % str(self.id)


class Word2VecModelDB(db.Model):
    __tablename__ = 'word_2_vec_model'

    id              = db.Column(db.Integer, primary_key=True)
    vocabulary_id   = db.Column(db.Integer, ForeignKey('skipp_gram_vocabulary.id'), nullable=False)
    dump_filename   = db.Column(String) 

    def __init__(self, vocabulary_id, 
            dump_filename):
        self.vocabulary_id = vocabulary_id
        self.dump_filename = dump_filename

    def __repr__(self):
        return '<W2VModel %r>' % str(self.id)

class VocabularyQueston(db.Model):
    __tablename__ = 'vocabulary_queston'

    id          = db.Column(db.Integer, primary_key=True)
    so_id       = db.Column(db.Integer)
    body        = db.Column(String) 
    title       = db.Column(String) 
    tags        = db.Column(String) 
    score       = db.Column(db.Integer)
    length      = db.Column(db.Integer)
    word_count  = db.Column(db.Integer)
    code_words  = db.Column(String) 
    
    filtered_words = db.Column(db.String) 
    question_words = db.Column(db.String)
    is_negative = db.Column(db.Boolean, default=True)

    def __init__(self, so_id, 
            body, 
            title, 
            tags, 
            score, 
            length, 
            word_count, 
            question_words,
            filtered_words, 
            code_words,
            is_negative):
        self.so_id      = so_id
        self.body       = body
        self.title      = title
        self.tags       = tags
        self.score      = score
        self.length     = length
        self.word_count = word_count
        self.code_words = code_words
        self.question_words = question_words
        self.filtered_words = filtered_words
        self.is_negative    = is_negative

    def __repr__(self):
        return '<VQues %r>' % str(self.id)

    @staticmethod
    def update_or_create(session, so_id, 
            body, 
            title, 
            tags, 
            score, 
            length, 
            word_count, 
            question_words,
            filtered_words, 
            code_words,
            is_negative):

        if session is None:
            local_session = db_session()
        
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
            if session is None:
                local_session.execute(update_query)
                local_session.commit()
                local_session.close()
            else:
                session.execute(update_query)

            return

        voc_qstn = VocabularyQueston(
            so_id, 
            body, 
            title, 
            tags, 
            score, 
            length, 
            word_count, 
            question_words, 
            filtered_words,
            code_words, 
            is_negative)

        if session is None:
            local_session.add(voc_qstn)
            local_session.commit()
            local_session.close()
        else:
            session.add(voc_qstn)  

    @staticmethod
    def count():
        session = db_session()
        count = session.query(func.count(VocabularyQueston.id)).scalar()
        session.close()
        return count

    @staticmethod
    def all():
        session = db_session()
        items = session.query(VocabularyQueston).distinct().all()
        session.close()
        return items
        
    @staticmethod
    def full_vocabualary():
        return VocabularyQueston.get_vocabualary()  

    @staticmethod
    def positive_vocabualary():
        return VocabularyQueston.get_vocabualary(True)  

    @staticmethod
    def get_vocabualary(only_positive=False):
        session = db_session()
        query = session.query(
                    func.string_agg(VocabularyQueston.filtered_words, 
                            aggregate_order_by(literal_column("' '"), 
                            VocabularyQueston.id)))
        if only_positive:
            query = query.filter(VocabularyQueston.is_negative==False)
        
        query = query.first()
        session.close()

        return u"%s" % str(query)  

    @staticmethod
    def test_data(length):
        session = db_session()
        items = session.query(VocabularyQueston).filter(VocabularyQueston.is_negative==False).order_by(func.random()).limit(length).all()
        session.close()
        return items                     

class VocabualaryQuestonWrapper():
    def __init__(self, only_positive=False):
        vocabualary = VocabularyQueston.positive_vocabualary() if only_positive else VocabularyQueston.full_vocabualary() 
        splited_vocabualary = str(vocabualary).split()
        indexies, most_common, dictionary, reversed_dictionary, vocabualary_size = self.build_dataset(splited_vocabualary)

        self.vocabualary        = vocabualary
        self.splited_vocabualary= splited_vocabualary
        self.indexies           = indexies
        self.most_common        = most_common
        self.dictionary         = dictionary
        self.reversed_dictionary= reversed_dictionary
        self.vocabualary_size   = vocabualary_size

    def build_dataset(self, vocabualary):
        count       = [['UNK', -1]]
        dictionary  = dict()
        indexies    = list()
        unk_count   = 0

        most_common = collections.Counter(vocabualary).most_common()
        vocabualary_size = len(most_common)
        count.extend(most_common)
        
        for word, _ in count:
            dictionary[word] = len(dictionary)
        
        for word in vocabualary:
            if word in dictionary:
                index = dictionary[word]
            else:
                index = 0  # dictionary['UNK']
                unk_count += 1
            indexies.append(index)

        count[0][1] = unk_count
        reversed_dictionary = dict(zip(dictionary.values(), dictionary.keys()))

        return indexies, count, dictionary, reversed_dictionary, vocabualary_size    

class NegativeExample(db.Model):
    __tablename__ = 'negative_example'

    id          = db.Column(db.Integer, primary_key=True)
    statement_id= db.Column(db.Integer, ForeignKey('statement.id'), nullable=True)
    body        = db.Column(String) 
    tags        = db.Column(String) 
    length      = db.Column(db.Integer)
    word_count  = db.Column(db.Integer)
    code_words  = db.Column(String) 
    
    filtered_words = db.Column(db.String) 
    question_words = db.Column(db.String)

    def __init__(self, body,  
            tags, 
            length, 
            word_count, 
            question_words,
            filtered_words, 
            code_words, statement_id=None):
        self.body       = body
        self.tags       = tags
        self.length     = length
        self.word_count = word_count
        self.code_words = code_words
        self.question_words = question_words
        self.filtered_words = filtered_words
        if statement_id is not None:
            self.statement_id = statement_id

    def __repr__(self):
        return '<NegExemple %r>' % str(self.id)

    @staticmethod
    def test_data():
        session = db_session()
        query = session.query(NegativeExample).join(Statement, NegativeExample.statement_id==Statement.id).\
                filter(and_(Statement.reviewed==True, Statement.false_assumption==True)).\
                distinct().\
                all()
        session.close()
        return query        


class TFModel(db.Model):
    __tablename__ = 'tf_model'

    id              = db.Column(db.Integer, primary_key=True)
    model_name      = db.Column(db.String) 
    dump_filename   = db.Column(db.String) 

    def __init__(self, model_name, 
            dump_filename):
        self.model_name = model_name
        self.dump_filename = dump_filename

    def __repr__(self):
        return '<TFModel %r>' % str(self.id)

    @staticmethod
    def get_last(model_name):
        session = db_session()
        query = session.query(TFModel).filter(TFModel.model_name==model_name).order_by(desc(TFModel.id)).first()
        session.close()

        return query.dump_filename

    @staticmethod
    def create_one(model_name, dump_filename):
        session = db_session()
        model = TFModel(model_name, dump_filename)
        session.add(model)
        session.commit()
        session.close()        
