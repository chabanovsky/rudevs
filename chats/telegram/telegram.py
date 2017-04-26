import datetime
import copy

import threading
import sched, time
from queue import Queue
from telethon import TelegramClient, RPCError
from telethon.tl.types import UpdatesTg, UpdateShortChatMessage, UpdateShortMessage, UpdateNewChannelMessage, UpdateChannel
from telethon.tl.types.channel import Channel
from telethon.utils import get_display_name

from sqlalchemy.sql import func, literal_column
from sqlalchemy import and_, not_, select, exists, delete, desc
from sqlalchemy.dialects.postgresql import aggregate_order_by

from models import TelegramChannel, TelegramTextMessage, TelegramUser, Statement
from meta import db_session
from local_settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_USER_PHONE
from analysis.analyse import QuestionAnalyser
from analysis.static_assessment import StaticAssessment

message_queue = Queue()
analyser = QuestionAnalyser()
static_assessment = StaticAssessment()
scheduler = sched.scheduler(time.time, time.sleep)

letters_per_min = 200
letters_per_second = letters_per_min // 60

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
        analyser_tread = threading.Thread(target=start_analysis_loop)
        analyser_tread.daemon = True
        analyser_tread.start()       
        while True:
            i = input('Enter q to stop: ')
            if i == 'q':
                return
    
    @staticmethod
    def telegram_on_message_callback(sender, msg, entity):    
        if not sender:
            print ("[telegram_on_message_callback] ERROR: no sender")
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
        if hasattr(msg, 'message'):
            content = msg.message
        else:
            print ("[telegram_on_message_callback] ERROR: hasattr(msg, 'message')")
            return

        # And print it to the user
        db_msg = TelegramTextMessage.query.\
            filter(and_(TelegramTextMessage.message_id==msg.id, TelegramTextMessage.channel_id==entity.id)).\
            first()
        creation_time = datetime.datetime.now()
        if not db_msg:
            print (creation_time.strftime('%H%:%M | %d.%m'), " [telegram_on_message_callback] new msg arrived")
            db_msg = TelegramTextMessage(msg.id, 
                    content, 
                    entity.id, 
                    sender.id, 
                    msg.reply_to_msg_id, 
                    creation_time)      
            session.add(db_msg)
            session.commit()
            
            global message_queue
            message_queue.put([entity.id, sender.id, msg.id, content, creation_time])
        else:
            print ("[telegram_on_message_callback] msg already in the DB")

        session.close()     

    def on_new_message(self, user, message, channel):
        #session = db_session()
        #min_id = session.query(TelegramTextMessage.message_id).\
        #    filter(TelegramTextMessage.channel_id==channel.id).\
        #    order_by(desc(TelegramTextMessage.message_id)).limit(1).scalar()
        #session.close()   
        #if min_id +1 != message.id:
        #    self.sync_telegram()
        #    return
        self.telegram_on_message_callback(user, message, channel)

    def on_new_channel (self, channel):
        self.sync_telegram()

    @staticmethod
    def update_handler(update_object, lisntener):
        if type(update_object) is not UpdatesTg:
            return

        WatchTelegramClient.threaded_update_handler([update_object, lisntener])

    @staticmethod
    def threaded_update_handler(args):
        update_object, lisntener = args

        if type(update_object.updates[0]) is UpdateNewChannelMessage:
            update = update_object.updates[0]
            message = update.message
            user = update_object.users[0]
            channel = update_object.chats[0]

            lisntener.on_new_message(user, message, channel)

        elif type(update_object.updates[0]) is UpdateChannel:
            channel = update_object.chats[0]
            lisntener.on_new_channel(channel)

def start_analysis_loop():
    static_assessment.load()

    min_to_end_stmnt = static_assessment.maximum_question_length // letters_per_min
    sec_to_end_stmnt = static_assessment.maximum_question_length // letters_per_second
    print ("[start_analysis_loop] min to end: ", min_to_end_stmnt, ", sec to end: ", sec_to_end_stmnt)

    # Analyse all that was not up to now
    do_analyse()

    current_exec_event = None
    while True:
        channel_id, user_id, message_id, message, creation_time = message_queue.get()
        created_ago = creation_time - datetime.timedelta(minutes=min_to_end_stmnt)
        updated_ago = creation_time - datetime.timedelta(seconds=(len(message) // letters_per_second))
        new_statment_was_created = False

        session = db_session()
        stmnt = Statement.query.\
                filter(and_(Statement.channel_id==channel_id, 
                    Statement.user_id==user_id,
                    Statement.created>created_ago,
                    Statement.updated>updated_ago)).\
                first()

        if stmnt is None:
            stmnt = Statement(channel_id, 
                user_id, 
                message_id,
                creation_time)
            session.add(stmnt)
            new_statment_was_created = True
            print("New stmnt (msgid): ", message_id)
        else:
            print("Update stmnt: ", stmnt.id)
            update_query = Statement.__table__.update().values(updated=creation_time, last_msg_id=message_id).\
                where(Statement.id==stmnt.id)
            session.execute(update_query)

        session.commit()
        session.close()

        do_analyse()

        if current_exec_event is not None:
            scheduler.cancel(current_exec_event)
            current_exec_event = None
        else:
            if  not scheduler.empty():
                print ("[start_analysis_loop] SYNC ERROR...")
        current_exec_event = scheduler.enter(sec_to_end_stmnt+5, 1, do_analyse)
        scheduler.run(blocking=False)
            
def do_analyse():
    print ("\r\n[do_analyse...]")
    min_to_end_stmnt = static_assessment.maximum_question_length // letters_per_min
    created_ago = datetime.datetime.now() - datetime.timedelta(minutes=min_to_end_stmnt)

    session = db_session()
    
    stmnts = session.query(Statement.id, Statement.channel_id, Statement.user_id, Statement.first_msg_id, Statement.last_msg_id).\
        filter(and_(Statement.created<created_ago, Statement.was_processed==False)).distinct().all()

    if stmnts is None or len(stmnts) == 0:
        print ("[do_analyse] nothing to process.") 
        return
    else:
        print ("[do_analyse] to process: ", len(stmnts)) 

    pairs = dict()
    for stmnt in stmnts:
        stmnt_id, channel_id, user_id, first_id, last_id = stmnt
        message_text = session.query(func.string_agg(TelegramTextMessage.message, 
                    aggregate_order_by(literal_column("'. '"), 
                            TelegramTextMessage.created))).\
                filter(and_(TelegramTextMessage.channel_id==channel_id, TelegramTextMessage.user_id==user_id)).\
                filter(TelegramTextMessage.message_id.between(first_id, last_id)).\
                distinct().\
                all()   
        pairs[stmnt_id] = message_text
    session.close()

    questions = list()
    not_question = list()
    for stmnt_id, message in pairs.items():
        if len(message) == 0:
            print ("[Message len error]")
            not_question.append(stmnt_id)
            continue

        is_question = analyser.validate(''.join(message[0])) 
        if is_question:
            questions.append(stmnt_id)       
        else:
            not_question.append(stmnt_id)

    session = db_session()

    if len(questions) > 0:
        print ("[do_analyse] questions found: ", len(questions))
        update_query = Statement.__table__.update().values(is_question=True, was_processed=True).\
            where(Statement.id.in_(questions))
        session.execute(update_query)

    if len(not_question) > 0:
        print ("[do_analyse] not questions: ", len(not_question))
        update_query_2 = Statement.__table__.update().values(is_question=False, was_processed=True).\
            where(Statement.id.in_(not_question))
        session.execute(update_query_2)

    session.commit()
    session.close()   
    print ("[do_analyse] done.")

