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

from meta import app as application, db, db_session, engine

@application.route("/index.html", endpoint="index")
@application.route("/", endpoint="index")
def index():
    return redirect(url_for('chats'))  

@application.route("/chats", endpoint="chats")
@application.route("/chats/", endpoint="chats")
def chats():
    return render_template('chats.html')
