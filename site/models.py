import datetime
import collections
import numpy as np
import csv

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, ColumnDefault
from sqlalchemy import and_, or_, desc
from sqlalchemy.sql import func, literal_column
from sqlalchemy.dialects.postgresql import aggregate_order_by

from meta import app as application, db, db_session, question_words_checker
from analysis.utils import process_text, process_code

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

    @staticmethod
    def get_negative():
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

        query_results = session.query(query.c.statement_id, query.c.agg_message, func.length(query.c.agg_message).label('len'), TelegramChannel.tags.label('tags')).\
            outerjoin(Statement, Statement.id==query.c.statement_id).\
            outerjoin(TelegramChannel, TelegramChannel.channel_id==Statement.channel_id).distinct().all()

        session.close()

        return query_results

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

class SourceData(db.Model):
    __tablename__ = 'source_data'

    source_type_so_question     = 1
    source_type_so_answer       = 2
    source_type_so_comment      = 3
    source_type_tl_statement    = 4
    source_type_so_bq_question  = 5

    id          = db.Column(db.Integer, primary_key=True)
    source_id   = db.Column(db.Integer)
    source_type = db.Column(db.Integer)
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

    def __init__(self, source_id,
            source_type, 
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
        self.source_id  = source_id
        self.source_type= source_type
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
    def update_or_create_raw(session, source_id, source_type, score, answer_count, title, body, tags, is_negative):
        length          = len(body)
        processed_body  = str(process_text(body, True, 2))
        code_words      = str(process_code(body))
        filtered_vocabualary = processed_body.split()
        tags            = tags.replace('|', " ")
        word_count      = len(filtered_vocabualary)
        question_words  = ""

        for word in filtered_vocabualary:
            if question_words_checker.is_question_word(word):
                question_words += " " + word

        SourceData.update_or_create(session,
            source_id, 
            source_type,
            body, 
            title, 
            tags, 
            score, 
            length, 
            word_count, 
            question_words, 
            processed_body,
            code_words, 
            is_negative)

    @staticmethod
    def update_or_create(session, 
            source_id, 
            source_type, 
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
        
        voc_qstn = SourceData.query.filter(and_(SourceData.source_id==source_id, SourceData.source_type==source_type)).first()
        if voc_qstn is not None:
            update_query = SourceData.__table__.update().values(
                    body=body, 
                    title=title,
                    tags=tags,
                    score=score,
                    length=length,
                    word_count=word_count,
                    code_words=code_words,
                    question_words=question_words).\
                where(SourceData.source_id==source_id)
            if session is None:
                local_session.execute(update_query)
                local_session.commit()
                local_session.close()
            else:
                session.execute(update_query)

            return

        voc_qstn = SourceData(
            source_id, 
            source_type,
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
        count = session.query(func.count(SourceData.id)).scalar()
        session.close()
        return count

    @staticmethod
    def all():
        session = db_session()
        items = session.query(SourceData).distinct().all()
        session.close()
        return items
        
    @staticmethod
    def full_vocabualary():
        return SourceData.get_vocabualary()  

    @staticmethod
    def positive_vocabualary():
        return SourceData.get_vocabualary(True)  

    @staticmethod
    def get_vocabualary(only_positive=False):
        session = db_session()
        query = session.query(
                    func.string_agg(SourceData.filtered_words, 
                            aggregate_order_by(literal_column("' '"), 
                            SourceData.id)))
        if only_positive:
            query = query.filter(SourceData.is_negative==False)
        
        query = query.first()
        session.close()

        return u"%s" % str(query)  

    @staticmethod
    def test_data(length, is_negative=False):
        session = db_session()
        if not is_negative:
            items = session.query(SourceData).filter(SourceData.is_negative==False).order_by(func.random()).limit(length).all()
        else:
            items = session.query(SourceData).filter(SourceData.source_type==SourceData.source_type_tl_statement).\
                join(Statement, SourceData.source_id==Statement.id).\
                filter(and_(Statement.reviewed==True, Statement.false_assumption==True)).\
                distinct().\
                all()

        session.close()
        return items   

    @staticmethod
    def load_all():        
        SourceData.load_good_questions()
        SourceData.load_good_answers()
        SourceData.load_spammy_answers()
        SourceData.load_spammy_comments()
        SourceData.load_spammy_questions()
        SourceData.load_bq_questions()
        SourceData.load_negative_statements()

    """
    Methods that help to upload data from csv files
    """
    @staticmethod
    def load_good_questions():
        print ("Starting loading good questions...")
        session = db_session()

        with open("data/questions.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, score, answer_count, title, body, tags = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_question, 
                        score, 
                        answer_count, 
                        title, 
                        body, 
                        tags, 
                        False)

        session.commit()
        session.close()

    @staticmethod
    def load_good_answers():
        print ("Starting loading good answers...")
        session = db_session()

        with open("data/answers.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, score, body, tags = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_answer, 
                        score, 
                        0, 
                        "", 
                        body, 
                        tags, 
                        False)

        session.commit()
        session.close()        

    @staticmethod
    def load_spammy_answers():
        print ("Starting loading spammy answers...")
        session = db_session()

        with open("data/spammy_answers.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, title, score, body, tags = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_answer, 
                        score, 
                        0, 
                        title, 
                        body, 
                        tags, 
                        True)

        session.commit()
        session.close()    

    @staticmethod
    def load_spammy_comments():
        print ("Starting loading spammy comments...")
        session = db_session()

        with open("data/spammy_comments.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, body, tags, score = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_answer, 
                        score, 
                        0, 
                        "", 
                        body, 
                        tags, 
                        True)

        session.commit()
        session.close()  

    @staticmethod
    def load_spammy_questions():
        print ("Starting loading spammy questions...")
        session = db_session()

        with open("data/spammy_questions.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, title, score, body, tags = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_question, 
                        score, 
                        0, 
                        title, 
                        body, 
                        tags, 
                        True)

        session.commit()
        session.close()  

    @staticmethod
    def load_bq_questions():
        print ("Starting loading bq questions...")
        session = db_session()

        with open("data/bq_questions.csv.csv", 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                source_id, title, body, tags, score = row
                
                SourceData.update_or_create_raw(session, 
                        source_id, 
                        SourceData.source_type_so_bq_question, 
                        score, 
                        0, 
                        title, 
                        body, 
                        tags, 
                        True)

        session.commit()
        session.close()  

    @staticmethod
    def load_negative_statements():
        print ("Starting loading negative statements...")
        items = Statement.get_negative()
        session = db_session()

        for item in items: 
            SourceData.update_or_create_raw(session, 
                item.statement_id,
                SourceData.source_type_tl_statement,
                0,
                0,
                "",
                item.agg_message,
                "",
                True)  

        session.commit()
        session.close()                                         

class SourceDataWrapper():
    def __init__(self, only_positive=False):
        vocabualary = SourceData.positive_vocabualary() if only_positive else SourceData.full_vocabualary() 
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
