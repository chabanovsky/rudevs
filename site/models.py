import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, ColumnDefault

from meta import app as application, db

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

    def __init__(self, channel_id, 
            user_id, 
            first_msg_id,
            created=datetime.datetime.now(),
            is_question=False,
            was_processed=False):
        self.channel_id     = channel_id
        self.user_id        = user_id
        self.first_msg_id   = first_msg_id
        self.last_msg_id    = first_msg_id
        self.created        = created
        self.updated        = created
        self.is_question    = is_question 
        self.was_processed  = was_processed

    def __repr__(self):
        return '<Stmnt %r>' % str(self.id)

class TelegramChannel(db.Model):
    __tablename__ = 'telegram_channel'

    id          = db.Column(db.Integer, primary_key=True)
    channel_id  = db.Column(db.BigInteger)
    title       = db.Column(db.String)
    username    = db.Column(db.String)
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
    is_positive = db.Column(db.Boolean, default=True)
    
    filtered_words = db.Column(db.String) 
    question_words = db.Column(db.String)

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
            is_positive):
        self.so_id      = so_id
        self.body       = body
        self.title      = title
        self.tags       = tags
        self.score      = score
        self.length     = length
        self.word_count = word_count
        self.is_positive= is_positive
        self.code_words = code_words
        self.question_words = question_words
        self.filtered_words = filtered_words

    def __repr__(self):
        return '<VQues %r>' % str(self.id)
