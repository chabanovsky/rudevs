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
    title = db.Column(db.String(100))
    username = db.Column(db.String(100))
    access_hash = db.Column(db.BigInteger)

    def __init__(self, channel_id, title, username, access_hash):
        self.channel_id = channel_id
        self.title = title
        self.username = username
        self.access_hash = access_hash

    def __repr__(self):
        return '<TChannel %r>' % str(self.id)
