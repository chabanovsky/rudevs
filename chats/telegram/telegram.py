import datetime

from telethon import TelegramClient, RPCError
from telethon.tl.types import UpdatesTg, UpdateShortChatMessage, UpdateShortMessage, UpdateNewChannelMessage, UpdateChannel
from telethon.tl.types.channel import Channel
from telethon.utils import get_display_name

from sqlalchemy.sql import func
from sqlalchemy import and_, not_, select, exists, delete, desc


from models import TelegramChannel, TelegramTextMessage, TelegramUser
from meta import db_session
from local_settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_USER_PHONE

class WatchTelegramClient(TelegramClient):
    dialog_count = 150
    message_count = 20
    
    def __init__(self, session_user_id='sessionid', 
            user_phone=str(TELEGRAM_USER_PHONE), 
            api_id=int(TELEGRAM_API_ID), 
            api_hash=str(TELEGRAM_API_HASH), 
            proxy=None):
        print('Initializing telegram watcher...')
        super().__init__(session_user_id, api_id, api_hash)

        print('Connecting to Telegram servers...')
        self.connect()

        if not self.is_user_authorized():
            print('First run. Sending code request...')
            self.send_code_request(user_phone)

            code_ok = False
            while not code_ok:
                code = input('Enter the code you just received: ')
                try:
                    code_ok = self.sign_in(user_phone, code)

                # Two-step verification may be enabled
                except RPCError as e:
                    if e.password_required:
                        pw = getpass(
                            'Two step verification is enabled. Please enter your password: ')
                        code_ok = self.sign_in(password=pw)
                    else:
                        raise e

    def get_channels(self):
        dialogs, entities = self.get_dialogs(self.dialog_count)
        result = list()
        for entity in entities:
            if not isinstance(entity, Channel):
                continue
            result.append(entity)
        return result

    def get_content(self, entities, output_callback):
        for entity in entities:
            total_count, messages, senders = self.get_message_history(
                        entity, limit=self.message_count, min_id=entity.min_id)
            content = None
            for msg, sender in zip(
                    reversed(messages), reversed(senders)):
                output_callback(sender, msg, entity)

    def subscribe_for_updates(self):
        # Listen for updates
        self.add_update_handler(lambda x: self.update_handler(x, self))

    def update_telegram_channels(self):
        channels = self.get_channels()
        session = db_session()
        ids = session.query(TelegramChannel)
        for entity in channels:
            channel = TelegramChannel.query.filter(TelegramChannel.channel_id==entity.id).first()
            if not channel:
                channel = TelegramChannel(entity.id, entity.title, entity.username, entity.access_hash)
                session.add(channel)
            else:
                channel.title = entity.title
                channel.username = entity.username
                channel.access_hash = entity.access_hash
            session.commit()
        session.close()
        return channels

    def sync_telegram(self):
        channels = self.update_telegram_channels()
        session = db_session()
        for channel in channels:
            min_id = session.query(TelegramTextMessage.message_id).\
                filter(TelegramTextMessage.channel_id==channel.id).\
                order_by(desc(TelegramTextMessage.message_id)).limit(1).scalar()
            if not min_id:
                min_id = 0
            setattr(channel, "min_id", min_id)
        session.close()
        self.get_content(channels, self.telegram_on_message_callback)



    def start(self):
        self.sync_telegram()
        self.subscribe_for_updates()        
        while True:
            i = input('Enter q to stop: ')
            if i == 'q':
                return
    
    @staticmethod
    def telegram_on_message_callback(sender, msg, entity):    
        if not sender:
            return

        session = db_session()
        user = TelegramUser.query.filter(TelegramUser.user_id==sender.id).first()
        if not user:
            user = TelegramUser(sender.id, 
                        sender.first_name, 
                        sender.last_name, 
                        sender.username)
            session.add(user)
            session.commit()
        
        # Format the message content
        if hasattr(msg, 'media') and msg.media:
            return
        else:
            if hasattr(msg, 'message'):
                content = msg.message
            else:
                return

        # And print it to the user
        db_msg = TelegramTextMessage.query.\
            filter(and_(TelegramTextMessage.message_id==msg.id, TelegramTextMessage.channel_id==entity.id)).\
            first()
        if not db_msg:
            db_msg = TelegramTextMessage(msg.id, content, entity.id, sender.id, msg.reply_to_msg_id)      
            session.add(db_msg)
            session.commit()
            print('[{}][{}:{}] (ID={}) {}: {}'.format(entity.username,
                msg.date.hour, msg.date.minute, msg.id, sender.first_name,
                content))

        session.close()     

    def on_new_message(self, user, message, channel):
        session = db_session()
        min_id = session.query(TelegramTextMessage.message_id).\
            filter(TelegramTextMessage.channel_id==channel.id).\
            order_by(desc(TelegramTextMessage.message_id)).limit(1).scalar()
        session.close()   
        if min_id +1 != message.id:
            self.sync_telegram()
            return
        self.telegram_on_message_callback(user, message, channel)

    def on_new_channel (self, channel):
        self.sync_telegram()

    @staticmethod
    def update_handler(update_object, lisntener):
        if type(update_object) is not UpdatesTg:
            return

        if type(update_object.updates[0]) is UpdateNewChannelMessage:
            update = update_object.updates[0]
            message = update.message
            user = update_object.users[0]
            channel = update_object.chats[0]

            lisntener.on_new_message(user, message, channel)

        elif type(update_object.updates[0]) is UpdateChannel:
            channel = update_object.chats[0]
            lisntener.on_new_channel(channel)