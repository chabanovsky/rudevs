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
from models import TelegramChannel

from sqlalchemy.sql import func
from sqlalchemy import and_, not_, select, exists, delete


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
                counter = 10

            client.get_content(channels)
            counter-=1
            time.sleep(5)

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