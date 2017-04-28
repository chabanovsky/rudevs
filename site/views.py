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


def get_statement_pagination(is_question, reviewed, page_num, per_page=DEFAULT_QUESTIONS_PER_PAGE):
    session = db_session()
    query = session.query(Statement.id, 
                Statement.channel_id, 
                Statement.user_id, 
                Statement.first_msg_id, 
                Statement.last_msg_id, 
                Statement.created,
                Statement.reviewed,
                Statement.false_assumption)

    if is_question is not None:
        query = query.filter(Statement.is_question==is_question)

    query = query.filter(and_(Statement.was_processed==True,
                    Statement.reviewed==reviewed)).\
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
    paginator = get_statement_pagination(True, False, page)
    return render_template('chats.html', paginator=paginator, base_url=url_for("chats"), active_tab="are_questions")

@application.route("/chats/not-questions", endpoint="chats_not_questions")
@application.route("/chats/not-questions/", endpoint="chats_not_questions")
def chats_not_questions():
    page = max(int(request.args.get("page", "1")), 1)
    paginator = get_statement_pagination(False, False, page)
    return render_template('chats.html', paginator=paginator, base_url=url_for("chats_not_questions"), active_tab="not_questions")    

@application.route("/chats/reviewed", endpoint="chats_reviewed")
@application.route("/chats/reviewed/", endpoint="chats_reviewed")
def chats_reviewed():
    page = max(int(request.args.get("page", "1")), 1)
    paginator = get_statement_pagination(None, True, page)
    return render_template('chats.html', paginator=paginator, base_url=url_for("chats_reviewed"), active_tab="reviewed")        

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

@application.route("/actions/actions_review/<stmnt_id>", endpoint="actions_review")
@application.route("/actions/actions_review/<stmnt_id>/", endpoint="actions_review")
def actions_review(stmnt_id):
    statement = Statement.query.filter_by(id=stmnt_id).first()
    if statement is None:
        abort(404)
    
    session = db_session()
    
    update_query = Statement.__table__.update().\
            values(reviewed=(not statement.reviewed)).\
            where(Statement.id==stmnt_id)
    session.execute(update_query)
    session.commit()
    session.close()

    resp = {
        "status": True,
        "msg": "OK",
        "stmnt_id": stmnt_id,
        "reviewed": not statement.reviewed
    }    

    return jsonify(**resp)
        
@application.route("/actions/extend_statement/<stmnt_id>", endpoint="actions_extend_statement")
@application.route("/actions/extend_statement/<stmnt_id>/", endpoint="actions_extend_statement")
def actions_extend_statement(stmnt_id,):
    statement = Statement.query.filter_by(id=stmnt_id).first()
    if statement is None:
        abort(404)

    action = int(request.args.get("action", "0"))
    if action == 0:
        abort(404)
    
    first_id = statement.first_msg_id
    last_id = statement.last_msg_id
        
    session = db_session()
    
    query = session.query(TelegramTextMessage.message_id).filter(
            and_(TelegramTextMessage.user_id==statement.user_id,
                    TelegramTextMessage.channel_id==statement.channel_id))

    if action == 1:
        first_id = query.filter(TelegramTextMessage.message_id<first_id).\
                order_by(desc(TelegramTextMessage.message_id)).distinct().first().message_id
    elif action == -1:
        first_id = query.filter(TelegramTextMessage.message_id>first_id).\
                order_by(TelegramTextMessage.message_id).distinct().first().message_id
    elif action == 2:
        last_id = query.filter(TelegramTextMessage.message_id>last_id).\
                order_by(TelegramTextMessage.message_id).distinct().first().message_id
    elif action == -2:
        last_id = query.filter(TelegramTextMessage.message_id<last_id).\
                order_by(desc(TelegramTextMessage.message_id)).distinct().first().message_id
    
    if first_id > last_id:
        resp = {
            "status": False,
            "msg": "Wrong range of ids",
            "stmnt_id": stmnt_id
        }    

        return jsonify(**resp)

    update_query = Statement.__table__.update().\
            values(first_msg_id=int(first_id),
                    last_msg_id=int(last_id)).\
            where(Statement.id==stmnt_id)

    session.execute(update_query)
    session.commit()
    session.close()

    resp = {
        "status": True,
        "msg": "OK",
        "stmnt_id": stmnt_id
    }    

    return jsonify(**resp)
                