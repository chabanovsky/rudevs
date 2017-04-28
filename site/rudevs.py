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
    from analysis.analyse import do_analyse, update_stored_data, do_validate, do_print_most_common_words, test_analyser, test_nltk, load_questions, do_auto_review, genereate_negative_examples

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
        if str(sys.argv[1]) == "--analyse":
            do_analyse()
            sys.exit()        
        if str(sys.argv[1]) == "--update_stored_data":
            update_stored_data()
            sys.exit()        
        if str(sys.argv[1]) == "--validate":
            do_validate()
            sys.exit()        
        if str(sys.argv[1]) == "--print_most_common":
            do_print_most_common_words()
            sys.exit()        
        if str(sys.argv[1]) == "--test_analyser":
            test_analyser()
            sys.exit()  
        if str(sys.argv[1]) == "--test_nltk":
            test_nltk()
            sys.exit()  
        if str(sys.argv[1]) == "--load_questions":
            load_questions()
            sys.exit()  
        if str(sys.argv[1]) == "--auto_review":
            do_auto_review()
            sys.exit()  
        if str(sys.argv[1]) == "--genereate_negative_examples":
            genereate_negative_examples()
            sys.exit()  
            

    app.run()