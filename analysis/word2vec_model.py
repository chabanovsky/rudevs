# encoding:utf-8
"""
This code basis was obtained from https://github.com/tensorflow/models/blob/master/tutorials/embedding/word2vec.py
"""

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

from models import SkippGramVocabulary, Word2VecModelDB
from meta import db_session
from sqlalchemy import desc

class Word2VecModel():
    filename = "questions.csv"
    vocabulary_size = 24000
    word_len_threshold = 3
    data_index = 0

    # train variables
    batch_size = 128
    embedding_size = 128    # Dimension of the embedding vector.
    skip_window = 10        # How many words to consider left and right.
    num_skips = 8           # How many times to reuse an input to generate a label.
    num_sampled = 64        # Number of negative examples to sample.
    num_steps = 100001


    # dataset variables
    data = list()
    count = list()
    dictionary = dict()
    reverse_dictionary = dict()

    def __init__(self, filename="questions.csv", debug_print=True, dump_filename="dump/word2vec_model"):
        self.filename = filename
        self.debug_print = debug_print
        self.dump_filename = dump_filename

    def read_question_data(self):
        data = ""
         # drop all words with lenght less then the threshold
        morph = pymorphy2.MorphAnalyzer()
        with open(self.filename, 'rt', encoding="utf8") as csvfile:
            csv_reader = csv.reader(csvfile, delimiter=',')
            for row in csv_reader:
                _, _, _, _, body, _ = row
                body = re.sub('<pre>.*?</pre>',' ', body, flags=re.DOTALL)
                body = re.sub('<code>.*?</code>',' ', body, flags=re.DOTALL)
                body = re.sub('<[^<]+?>', ' ', body) 
                body = body.replace(",", " ")
                body = body.replace(".", " ")
                body = body.replace("?", " ")
                body = body.replace("\n", " ")
                body = body.replace("\\\n", " ")
                body = body.replace("\\\\n", " ")
                body = body.replace("(", " ")
                body = body.replace(")", " ")
                body = body.replace(":", " ")
                body = body.replace(";", " ")
                body = body.replace("\'", " ")
                body = body.replace("\\'", " ")
                body = body.replace("\\", " ")
                body = body.replace("\"", " ")
                body = body.replace("/", " ")
                body = body.replace("|", " ")
                body = body.strip()
                
                for word in body.lower().split(" "):
                    if len(word) < self.word_len_threshold:
                        continue
                    p = morph.parse(word)[0]
                    # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
                    if str(p.tag) in ['LATN', 'PNCT', 'NUMB', 'UNKN']:
                        continue
                    # http://pymorphy2.readthedocs.io/en/latest/user/grammemes.html
                    if str(p.tag.POS) not in ['NPRO', 'PRED', 'PREP', 'CONJ', 'PRCL', 'INTJ']:
                        data += " " +  p.normal_form
        return data


    def build_dataset(self, words, n_words):
        """Process raw inputs into a dataset."""
        count = [['UNK', -1]]
        count.extend(collections.Counter(words).most_common(n_words - 1))
        dictionary = dict()
        for word, _ in count:
            dictionary[word] = len(dictionary)
        data = list()
        unk_count = 0
        for word in words:
            if word in dictionary:
                index = dictionary[word]
            else:
                index = 0  # dictionary['UNK']
                unk_count += 1
            data.append(index)
        count[0][1] = unk_count
        reversed_dictionary = dict(zip(dictionary.values(), dictionary.keys()))
        return data, count, dictionary, reversed_dictionary

    def generate_batch(self, batch_size, num_skips, skip_window, data):
        assert batch_size % num_skips == 0
        assert num_skips <= 2 * skip_window

        batch = np.ndarray(shape=(batch_size), dtype=np.int32)
        labels = np.ndarray(shape=(batch_size, 1), dtype=np.int32)
        span = 2 * skip_window + 1  # [ skip_window target skip_window ]
        buffer = collections.deque(maxlen=span)

        for _ in range(span):
            buffer.append(data[self.data_index])
            self.data_index = (self.data_index + 1) % len(data)
            
        for i in range(batch_size // num_skips):
            target = skip_window  # target label at the center of the buffer
            targets_to_avoid = [skip_window]
            for j in range(num_skips):
                while target in targets_to_avoid:
                    target = random.randint(0, span - 1)
                targets_to_avoid.append(target)

                batch[i * num_skips + j] = buffer[skip_window]
                labels[i * num_skips + j, 0] = buffer[target]

            buffer.append(data[self.data_index])
            self.data_index = (self.data_index + 1) % len(data)

        # Backtrack a little bit to avoid skipping words in the end of a batch
        self.data_index = (self.data_index + len(data) - span) % len(data)
        return batch, labels

    def plot_with_labels(self, low_dim_embs, labels, filename='./dump/tsne.png'):
        assert low_dim_embs.shape[0] >= len(labels), 'More labels than embeddings'
        plt.figure(figsize=(18, 18))  # in inches
        for i, label in enumerate(labels):
            x, y = low_dim_embs[i, :]
            plt.scatter(x, y)
            plt.annotate(label,
                        xy=(x, y),
                        xytext=(5, 2),
                        textcoords='offset points',
                        ha='right',
                        va='bottom')

        plt.savefig(filename)

    def update_train_data(self):
        vocabulary = self.read_question_data()
        db_vocabulary_item = SkippGramVocabulary(vocabulary)
        session = db_session()
        session.add(db_vocabulary_item)
        session.commit()
        session.close()

    def upload_dataset(self, id=None):
        session = db_session()
        if id is None:
            query = session.query(SkippGramVocabulary.id, SkippGramVocabulary.vocabulary).order_by(desc(SkippGramVocabulary.id))
        else:
            query = session.query(SkippGramVocabulary.id, SkippGramVocabulary.vocabulary).filter(SkippGramVocabulary.id==id)
        db_item = query.first()
        vocabulary = str(db_item.vocabulary)
        vocabulary_id = int(db_item.id)
        session.close()
        # Build the dictionary and replace rare words with UNK token.
        # data: a set of indexes of words in the "dictionary"
        # count: a dictionary where key is a word, value is the word frequency
        # dictionary: a dictionary where key is a word, value is an index of in an array of the words sorted by frequency
        # reverse_dictionary: a reversed version of the "dictionary"

        self.data, self.count, self.dictionary, self.reverse_dictionary = self.build_dataset(
                tf.compat.as_str(vocabulary).split(), 
                self.vocabulary_size)
        del vocabulary  

        return vocabulary_id

    def visualise(self, final_embeddings, reverse_dictionary, filename="./dump/tsne.png"):
        tsne = TSNE(perplexity=30, n_components=2, init='pca', n_iter=5000)
        plot_only = 500
        x_embeddings = final_embeddings[:plot_only, :]
        print("___________________")
        print(x_embeddings)
        low_dim_embs = tsne.fit_transform(x_embeddings)
        labels = [reverse_dictionary[i] for i in xrange(plot_only)]
        self.plot_with_labels(low_dim_embs, labels, filename)

    def restore_last(self):
        session = db_session()
        query = session.query(Word2VecModelDB.vocabulary_id, Word2VecModelDB.dump_filename).order_by(desc(Word2VecModelDB.id))
        db_item = query.first()
        dump_filename = str(db_item.dump_filename)
        vocabulary_id = int(db_item.vocabulary_id)
        session.close()

        self.upload_dataset(vocabulary_id)
        return dump_filename
    
    def upload_saved_data_for_model():
        dump_filename = self.restore_last()
        graph, saver, init = self.declare_tf()
        return dump_filename

    def validate_examples(self):
        # We pick a random validation set to sample nearest neighbors. Here we limit the
        # validation samples to the words that have a low numeric ID, which by
        # construction are also the most frequent.
        valid_size = 16     # Random set of words to evaluate similarity on.
        valid_window = 16  # Only pick dev samples in the head of the distribution.
        # valid_window: top value
        # valid_size: number of elements
        valid_examples = np.random.choice(valid_window, valid_size, replace=False)

        dump_filename = self.restore_last()
        graph, saver  = self.declare_tf()

        with graph.as_default():
            norm =  tf.sqrt(tf.reduce_sum(tf.square(self.embeddings), 1, keep_dims=True))
            normalized_embeddings = self.embeddings / norm

            valid_dataset = tf.constant(valid_examples, dtype=tf.int32)
            # valid_dataset - ids of rows to extract from the normalized_embeddings
            valid_embeddings = tf.nn.embedding_lookup(
                    normalized_embeddings, valid_dataset)
            similarity = tf.matmul(
                    valid_embeddings, normalized_embeddings, transpose_b=True)

        with tf.Session(graph=graph) as session:
            saver.restore(session, dump_filename)

            # Note that this is expensive (~20% slowdown if computed every 500 steps)
            sim = similarity.eval()
            for i in xrange(valid_size):
                valid_word = self.reverse_dictionary[valid_examples[i]]
                top_k = 8  # number of nearest neighbors
                nearest = (-sim[i, :]).argsort()[1:top_k + 1]
                log_str = 'Nearest to %s:' % valid_word
                for k in xrange(top_k):
                    close_word = self.reverse_dictionary[nearest[k]]
                    log_str = '%s %s,' % (log_str, close_word)
                print(log_str)

            if self.debug_print:
                self.visualise(self.embeddings.eval(), self.reverse_dictionary, "tsne_validate.png")
        
    def declare_tf(self):
        self.graph = tf.Graph()

        with self.graph.as_default():
            # Input data.
            self.train_inputs = tf.placeholder(tf.int32, shape=[self.batch_size], name="train_inputs")
            self.train_labels = tf.placeholder(tf.int32, shape=[self.batch_size, 1], name="train_labels")
            

            # Ops and variables pinned to the CPU because of missing GPU implementation
            with tf.device('/cpu:0'):
                # Look up embeddings for inputs.
                # tf.random_uniform - fills out shape with numbers from -1.0 to 1.0
                # vocabulary_size - num of rows
                # embedding_size - num of comumns
                self.embeddings = tf.Variable(tf.random_uniform([self.vocabulary_size, self.embedding_size], -1.0, 1.0), name="embeddings")
                # embed = embeddings[train_inputs[i] i = 1.. N, []], ie change each i-th row 
                self.embed = tf.nn.embedding_lookup(self.embeddings, self.train_inputs, name="embed")

                # Construct the variables for the NCE loss
                # Outputs random values from a truncated normal distribution.
                # The generated values follow a normal distribution with specified mean and standard deviation, 
                # except that values whose magnitude is more than 2 standard deviations 
                # from the mean are dropped and re-picked
                self.nce_weights = tf.Variable(tf.truncated_normal([self.vocabulary_size, self.embedding_size], stddev=1.0 / math.sqrt(self.embedding_size)), name="nce_weights")
                self.nce_biases = tf.Variable(tf.zeros([self.vocabulary_size]), name="nce_biases")

            # Compute the average NCE loss for the batch.
            # tf.nce_loss automatically draws a new sample of the negative labels each
            # time we evaluate the loss.
            self.loss = tf.reduce_mean(
                tf.nn.nce_loss(weights=self.nce_weights,
                                biases=self.nce_biases,
                                labels=self.train_labels,
                                inputs=self.embed,
                                num_sampled=self.num_sampled,
                                num_classes=self.vocabulary_size), name="loss")

            # Construct the SGD optimizer using a learning rate of 1.0.
            self.optimizer = tf.train.GradientDescentOptimizer(1.0).minimize(self.loss)

            self.saver = tf.train.Saver()

            return self.graph, self.saver


    def train(self):
        vocabulary_id = self.upload_dataset()

        if self.debug_print:
            print("Number of different words: ", len(self.count))
            print('Most common words (+UNK)', self.count[:5])
            print('Sample data', self.data[:10], [self.reverse_dictionary[i] for i in self.data[:10]])
        
        _, _ = self.declare_tf()

        with self.graph.as_default():
            init = tf.global_variables_initializer()

        with tf.Session(graph=self.graph) as session:
            # We must initialize all variables before we use them.
            init.run()
            if self.debug_print:
                print('Initialized')

            average_loss = 0
            for step in xrange(self.num_steps):
                batch_inputs, batch_labels = self.generate_batch(
                    self.batch_size, self.num_skips, self.skip_window, self.data)
                feed_dict = {self.train_inputs: batch_inputs, self.train_labels: batch_labels}

                # We perform one update step by evaluating the optimizer op (including it
                # in the list of returned values for session.run()
                _, loss_val = session.run([self.optimizer, self.loss], feed_dict=feed_dict)
                average_loss += loss_val

                if self.debug_print:
                    if step % 2000 == 0:
                        if step > 0:
                            average_loss /= 2000
                        # The average loss is an estimate of the loss over the last 2000 batches.
                        print('Average loss at step ', step, ': ', average_loss)
                        average_loss = 0
            
            save_path = self.saver.save(session, self.dump_filename)
            pg_session = db_session()
            w2vmdl = Word2VecModelDB(vocabulary_id, save_path)
            pg_session.add(w2vmdl)
            pg_session.commit()
            pg_session.close()

            if self.debug_print:
                self.visualise(self.embeddings.eval(), self.reverse_dictionary)
                self.visualise(self.embeddings.eval(), self.reverse_dictionary, "./dump/tsne_2.png")