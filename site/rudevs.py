import sys
import os
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib'))
sys.path.append(os.path.abspath(os.getcwd()))    
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), os.pardir)))
sys.path.append("/development/Telethon")    
sys.path.append("/development/Telethon/telethon")    

if sys.version_info[0] >= 3:
    from chats.telegram.telegram import WatchTelegramClient
    from analysis.analyse import do_print_most_common_words, test_analyser, load_source_data, do_auto_review, upload_big_questions

from meta import *
from views import *
from filters import *

if __name__ == "__main__":
    if len(sys.argv) > 1:
        from database import init_db
        if str(sys.argv[1]) == "--init_db":
            init_db()
            sys.exit()
        if str(sys.argv[1]) == "--start_telegram":
            client = None
            try:
                client = WatchTelegramClient()
                client.start()
            finally:
                if client:
                    client = client.disconnect()
            sys.exit()        
        if str(sys.argv[1]) == "--print_most_common":
            do_print_most_common_words()
            sys.exit()        
        if str(sys.argv[1]) == "--test_analyser":
            test_analyser()
            sys.exit()  
        if str(sys.argv[1]) == "--load_source_data":
            load_source_data()
            sys.exit()  
        if str(sys.argv[1]) == "--auto_review":
            do_auto_review()
            sys.exit()  
        if str(sys.argv[1]) == "--upload_big_questions":
            upload_big_questions()
            sys.exit()  

    app.run()