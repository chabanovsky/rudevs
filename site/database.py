import csv
import os
import re
from datetime import datetime

import logging
from meta import db, db_session, engine
from models import Statement, TelegramChannel, SkippGramVocabulary, Word2VecModelDB
from sqlalchemy.sql import func
from sqlalchemy import and_, not_, select, exists, delete

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    db.create_all()
