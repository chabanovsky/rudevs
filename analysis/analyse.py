# encoding:utf-8
"""Basic word2vec example."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import csv
import collections
import math
import os
import random
import zipfile
import re

import pymorphy2
import numpy as np
from six.moves import urllib
from six.moves import xrange  # pylint: disable=redefined-builtin
import tensorflow as tf

from sklearn.manifold import TSNE
import matplotlib.pyplot as plt

from models import SkippGramVocabulary
from meta import db_session
from sqlalchemy import desc
from analysis.word2vec_model import Word2VecModel


def update_stored_data():
    model = Word2VecModel()
    model.update_train_data()
    
def do_analyse():
    model = Word2VecModel()
    model.train()
    model.validate_examples()
    
def do_validate():
    model = Word2VecModel()
    model.validate_examples()