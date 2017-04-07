import sys
import os
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib'))
sys.path.append(os.getcwd())    
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), os.pardir)))

if sys.version_info[0] >= 3:
    from telethon import RPCError
    from telethon.tl.types.channel import Channel
    from chats.telegram.telegram import WatchTelegramClient

from meta import *
from views import *
from filters import *
from models import TelegramChannel, TelegramTextMessage, TelegramUser

from sqlalchemy.sql import func
from sqlalchemy import and_, not_, select, exists, delete

def telegram_on_message_callback(sender, msg, entity):    
    if not sender:
        return

    session = db_session()
    user = TelegramUser.query.filter(TelegramUser.user_id==sender.id).first()
    if not user:
        user = TelegramUser(sender.id, 
                    sender.first_name, 
                    sender.last_name, 
                    sender.username, 
                    sender.access_hash)
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
    db_msg = TelegramTextMessage.query.filter(and_(TelegramTextMessage.message_id==msg.id, TelegramTextMessage.channel_id==entity.id)).first()
    if not db_msg:
        db_msg = TelegramTextMessage(msg.id, content, entity.id, sender.id)      
        session.add(db_msg)
        session.commit()
        print('[{}:{}] (ID={}) {}: {}'.format(
            msg.date.hour, msg.date.minute, msg.id, sender.first_name,
            content))

    session.close()     


def update_telegram_channels(client):
    channels = client.get_channels()
    session = db_session()
    ids = session.query(TelegramChannel)
    for entity in channels:
        channel = TelegramChannel.query.filter(TelegramChannel.channel_id==entity.id).first()
        if not channel:
            channel = TelegramChannel(entity.id,entity.title, entity.username, entity.access_hash)
            session.add(channel)
        else:
            channel.title = entity.title
            channel.username = entity.username
            channel.access_hash = entity.access_hash
        session.commit()
    session.close()
    return channels

def watch_telegram():
    client = None
    try:
        client = WatchTelegramClient()        
        counter = 0
        while True:
            if counter <= 0:
                channels = update_telegram_channels(client)
                counter = 50
            session = db_session()
            for channel in channels:
                min_id = session.query(TelegramTextMessage.message_id).filter(TelegramTextMessage.channel_id==channel.id).order_by(desc(TelegramTextMessage.message_id)).limit(1).scalar()
                setattr(channel, "min_id", min_id)
            session.close()

            client.get_content(channels, telegram_on_message_callback)
            counter-=1
            time.sleep(10)

    except RPCError:
        watch_telegram()
    finally:
        if client:
            client.disconnect()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        from database import init_db
        if str(sys.argv[1]) == "--init_db":
            init_db()
            sys.exit()
        if str(sys.argv[1]) == "--start_telegram":
            watch_telegram()
            sys.exit()        

    app.run()