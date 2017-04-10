import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, ColumnDefault

from meta import app as application, db

class Statement(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.Integer)
    text = db.Column(db.Integer)
    username = db.Column(db.String(100))
    date = db.Column(db.DateTime, nullable=True)

    def __init__(self, channel, text, username, date):
        self.channel = channel
        self.text = text
        self.username = username
        self.date = date

    def __repr__(self):
        return '<Statement %r>' % str(self.id)

class TelegramChannel(db.Model):
    __tablename__ = 'telegram_channel'

    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.BigInteger)
    title = db.Column(db.String)
    username = db.Column(db.String)
    access_hash = db.Column(db.BigInteger)

    def __init__(self, channel_id, title, username, access_hash):
        self.channel_id = channel_id
        self.title = title
        self.username = username
        self.access_hash = access_hash

    def __repr__(self):
        return '<TChannel %r>' % str(self.id)

class TelegramTextMessage(db.Model):
    __tablename__ = 'telegram_text_message'

    id = db.Column(db.Integer, primary_key=True)
    message_id = db.Column(db.BigInteger)
    message = db.Column(db.String)
    date = db.Column(db.DateTime, default=datetime.datetime.now)
    channel_id = Column(db.BigInteger)
    user_id = Column(db.BigInteger)
    reply_to_id = db.Column(db.BigInteger)

    def __init__(self, message_id, message, channel_id, user_id, reply_to_id):
        self.message_id = message_id
        self.message = message
        self.channel_id = channel_id
        self.user_id = user_id
        self.reply_to_id = reply_to_id

    def __repr__(self):
        return '<TTxtMsg %r>' % str(self.id)

class TelegramUser(db.Model):
    __tablename__ = 'telegram_user'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    username = db.Column(db.String)

    def __init__(self, user_id, first_name, last_name, username):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

    def __repr__(self):
        return '<TUser %r>' % str(self.id)
