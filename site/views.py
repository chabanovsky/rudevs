# encoding:utf-8
import requests
import logging
import json
import urllib
import re
try:
    from urllib.parse import urlparse
except:
     from urlparse import urlparse

from flask import Flask, jsonify, render_template, g, url_for, redirect, request, session, abort, make_response
from flask.ext.babel import gettext, ngettext
from sqlalchemy import and_, desc
from sqlalchemy.sql import func
from flask.ext.sqlalchemy import Pagination

from meta import app as application, db, db_session, engine
from models import TelegramTextMessage, Statement
DEFAULT_QUESTIONS_PER_PAGE = 15

def pagination_helper(page_num, per_page, question_query):
    total = question_query.count()
    items = question_query.offset((page_num-1)*per_page).limit(per_page).all()
    p = Pagination(question_query, page_num, per_page, total, items)
    return p     


def get_statement_pagination(page_num, per_page=DEFAULT_QUESTIONS_PER_PAGE):
    session = db_session()
    query = session.query(Statement.id, 
                Statement.channel_id, 
                Statement.user_id, 
                Statement.first_msg_id, 
                Statement.last_msg_id, 
                Statement.created).\
            filter(and_(Statement.is_question==True, Statement.was_processed==True)).\
            order_by(desc(Statement.created))

    pag = pagination_helper(page_num, per_page, query)
    session.close()
    return pag     

@application.route("/index.html", endpoint="index")
@application.route("/", endpoint="index")
def index():
    return redirect(url_for('chats'))  

@application.route("/chats", endpoint="chats")
@application.route("/chats/", endpoint="chats")
def chats():
    page = max(int(request.args.get("page", "1")), 1)
    paginator = get_statement_pagination(page)
    return render_template('chats.html', paginator=paginator, base_url=url_for("chats"))

@application.route("/chats/statement/<stmnt_id>", endpoint="chat_statement")
@application.route("/chats/statement/<stmnt_id>/", endpoint="chat_statement")
def chat_statement(stmnt_id):
    statement = Statement.query.filter_by(id=int(stmnt_id)).first()
    if statement is None:
        abort(404)
    return render_template('chat_statement.html', statement=statement)

@application.route("/actions/mark_false/<stmnt_id>", endpoint="actions_mark_false")
@application.route("/actions/mark_false/<stmnt_id>/", endpoint="actions_mark_false")
def actions_mark_false(stmnt_id):
    statement = Statement.query.filter_by(id=stmnt_id).first()
    if statement is None:
        abort(404)
    
    session = db_session()
    
    update_query = Statement.__table__.update().\
            values(false_assumption=(not statement.false_assumption)).\
            where(Statement.id==stmnt_id)
    session.execute(update_query)
    session.commit()
    session.close()

    resp = {
        "status": True,
        "msg": "OK",
        "stmnt_id": stmnt_id,
        "false_assumption": not statement.false_assumption
    }    

    return jsonify(**resp)
    