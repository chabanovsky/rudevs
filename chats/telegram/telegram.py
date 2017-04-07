import datetime

from telethon import TelegramClient, RPCError
from telethon.tl.types import UpdateShortChatMessage, UpdateShortMessage
from telethon.tl.types.channel import Channel
from telethon.utils import get_display_name

from local_settings import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_USER_PHONE

class WatchTelegramClient(TelegramClient):
    dialog_count = 100
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

    def get_content(self, entities):
        for entity in entities:
            total_count, messages, senders = self.get_message_history(
                        entity, limit=self.message_count)
            content = None
            for msg, sender in zip(
                    reversed(messages), reversed(senders)):
                # Get the name of the sender if any
                name = sender.first_name if sender else ''
                # Format the message content
                if hasattr(msg, 'media') and msg.media:
                    content = '<{}> {}'.format(  # The media may or may not have a caption
                        msg.media.__class__.__name__,
                        getattr(msg.media, 'caption', ''))
                else:
                    if hasattr(msg, 'message'):
                        content = msg.message
                    else:
                        content = ""
                if content:
                    # And print it to the user
                    print('[{}:{}] (ID={}) {}: {}'.format(
                        msg.date.hour, msg.date.minute, msg.id, name,
                        content))                

        


    @staticmethod
    def update_handler(update_object):
        if type(update_object) is UpdateShortMessage:
            if update_object.out:
                print('You sent {} to user #{}'.format(update_object.message,
                                                       update_object.user_id))
            else:
                print('[User #{} sent {}]'.format(update_object.user_id,
                                                  update_object.message))

        elif type(update_object) is UpdateShortChatMessage:
            if update_object.out:
                print('You sent {} to chat #{}'.format(update_object.message,
                                                       update_object.chat_id))
            else:
                print('[Chat #{}, user #{} sent {}]'.format(
                    update_object.chat_id, update_object.from_id,
                    update_object.message))

