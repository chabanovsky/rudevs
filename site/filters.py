
from sqlalchemy.sql import func, literal_column
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy import and_, desc

from jinja2 import evalcontextfilter, Markup
import babel

from meta import app as application, LANGUAGE, db_session
from models import TelegramTextMessage, TelegramChannel

@application.template_filter()
@evalcontextfilter
def generate_string(eval_ctx, localized_value):
    if localized_value is None:
        return ""
    else:
        return Markup("\"" + localized_value + "\"").unescape()        

def current_language():
    return LANGUAGE

def statement_messages(statement):
    session = db_session()

    message_text = session.query(func.string_agg(TelegramTextMessage.message, 
                aggregate_order_by(literal_column("'. '"), 
                        TelegramTextMessage.message))).\
            filter(and_(TelegramTextMessage.channel_id==statement.channel_id,
                    TelegramTextMessage.user_id==statement.user_id)).\
            filter(TelegramTextMessage.message_id.between(statement.first_msg_id, 
                    statement.last_msg_id)).\
            distinct().\
            all()   

    message_text = ''.join(message_text[0])        
    session.close()

    return message_text

def message_list(statement, range=15):  
    session = db_session()  
    messages = session.query(TelegramTextMessage.message_id,
                TelegramTextMessage.channel_id,
                TelegramTextMessage.user_id,
                TelegramTextMessage.created,
                TelegramTextMessage.message).\
            filter(and_(TelegramTextMessage.channel_id==statement.channel_id,
                TelegramTextMessage.message_id.between(max(0, statement.first_msg_id-range), 
                    statement.last_msg_id+range))).\
            order_by(TelegramTextMessage.created).\
            distinct().\
            all()

    session.close()
    return messages

def stmnt_channel_info(statement):
    session = db_session()
    channel = session.query(TelegramChannel.title, TelegramChannel.username).\
            filter(TelegramChannel.channel_id==statement.channel_id).first()
    session.close()
    return channel

application.jinja_env.globals.update(current_language=current_language, 
        statement_messages=statement_messages,
        stmnt_channel_info=stmnt_channel_info,
        message_list=message_list)     