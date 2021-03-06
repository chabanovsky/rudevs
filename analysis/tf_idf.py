
import math
import os
import random
import zipfile
import re
import sys
import collections
import numpy as np
import string

import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer

from models import SourceData, SourceDataWrapper, TFModel
from analysis.utils import process_text

class TfIdfData():
    def __init__(self, vocabualary_size=None):
        self.helper         = SourceDataWrapper()
        self.num_classes    = 2
        if vocabualary_size is None:
            self.max_features = self.helper.vocabualary_size
        else:
            n = (self.helper.vocabualary_size // vocabualary_size)
            n = (n if n % 2 == 0 else n + 1)
            while n % 4 != 0:
                n = n + 2
            self.max_features = n 

        self.texts      = list()
        self.labels     = np.empty(shape=(0, self.num_classes))
        self.documents  = SourceData.all()

        print("Number of documetnts to train: ", len(self.documents))

        for document in self.documents:
            self.texts.append(tf.compat.as_str(document.filtered_words))
            negative = 1 if document.is_negative else 0
            positive = 0 if document.is_negative else 1
            self.labels = np.append(self.labels, [[negative, positive]], axis=0)

        self.tfidf = TfidfVectorizer(tokenizer=lambda text: text.split(), max_features=self.max_features)
        self.sparse_tfidf_texts = self.tfidf.fit_transform(self.texts)

        self.index = 0
    
    def make_vector(self, string):
        return self.tfidf.transform(string)

    def get_batch(self, batch_size):
        # sparse_tfidf_texts.shape[0] - number of documents, i. e. strings.
        # sparse_tfidf_texts.shape[2] - number of features, i. e. len of vocabualary.
        if self.index >= self.sparse_tfidf_texts.shape[0]:
            self.index = 0

        if self.index + batch_size >= self.sparse_tfidf_texts.shape[0]:    
            self.index = self.sparse_tfidf_texts.shape[0] - batch_size

        rand_index = random.sample(range(self.index, self.index+batch_size), batch_size)
        text_batch  = self.sparse_tfidf_texts[rand_index].todense()
        label_batch = self.labels[rand_index]

        self.index = self.index + batch_size
        return text_batch, label_batch

    def num_features(self):
        return self.max_features

class TFIDFModelBase():
    def __init__(self, data_vocabualary_size=None):
        self.data = TfIdfData(data_vocabualary_size)
        self.dump_filename = "dump/%s" % self.model_name()

    def model_name(self):
        raise NotImplementedError("model_name")

    def restore_last(self):
        saving_filename = TFModel.get_last(self.model_name())
        print ("saving_filename: ", saving_filename)
        self.declare_tf()

        self.session = tf.InteractiveSession(graph=self.graph)
        self.saver.restore(self.session, saving_filename)  

    def validate_model(self):
        documents   = SourceData.test_data(50, True)
        texts       = list()
        labels      = np.empty(shape=(0, self.data.num_classes))

        print("Number of documetnts to validate: ", len(documents))

        for document in documents:
            texts.append(tf.compat.as_str(document.filtered_words))
            negative = 1 
            positive = 0
            labels = np.append(labels, [[negative, positive]], axis=0)

        sparse_tfidf_texts = self.data.tfidf.transform(texts)
        rand_index = np.random.choice(sparse_tfidf_texts.shape[0], size=len(documents))
        text_batch  = sparse_tfidf_texts[rand_index].todense()
        label_batch = labels[rand_index]     
        return text_batch, label_batch  
        

class TfIdfModel(TFIDFModelBase):
    def __init__(self):
        super(TfIdfModel, self).__init__(2)

        self.num_steps  = 10000
        self.batch_size = 200

    def model_name(self):
        return "tfidf_simple"       

    def train(self):
        self.declare_tf()
        with self.graph.as_default():
            init = tf.global_variables_initializer()
        self.session = tf.InteractiveSession(graph=self.graph)
        init.run()

        for step in range(self.num_steps):
            if (step%100) == 0:
                print  ("Step: ", step) 
            text_batch, label_batch  = self.data.get_batch(self.batch_size)

            self.session.run(self.train_step, feed_dict={self.x: text_batch, self.y_: label_batch})

        saving_path = self.saver.save(self.session, self.dump_filename)
        TFModel.create_one(self.model_name(), saving_path)
        print ("Saved as ", saving_path)

    def declare_tf(self):
        self.graph = tf.Graph()
        with self.graph.as_default():
            self.x = tf.placeholder(tf.float32, [None, self.data.num_features()], name="x")
            # We have only two classes
            self.b = tf.Variable(tf.zeros([self.data.num_classes]), name="b")
            self.W = tf.Variable(tf.zeros([self.data.num_features(), self.data.num_classes]), name="W")
            # Calculated probability of classes
            self.y = tf.add(tf.matmul(self.x, self.W), self.b, name="y")
            # Our real classes. It should have sites of self.data.num_features() x self.data.num_classes
            self.y_ = tf.placeholder(tf.float32, [None, self.data.num_classes], name="y_")

            #   tf.reduce_mean(-tf.reduce_sum(y_ * tf.log(tf.nn.softmax(y)),
            #                                 reduction_indices=[1]))        
            self.cross_entropy = tf.reduce_mean(
                    tf.nn.sigmoid_cross_entropy_with_logits(labels=self.y_, logits=self.y), name="cross_entropy")
            self.train_step = tf.train.GradientDescentOptimizer(0.5).minimize(self.cross_entropy)

            self.correct_prediction = tf.equal(tf.argmax(self.y, 1), tf.argmax(self.y_, 1), name="correct_prediction")
            self.accuracy = tf.reduce_mean(tf.cast(self.correct_prediction, tf.float32), name="accuracy")
            
            self.saver = tf.train.Saver(tf.global_variables())


    def validate_model(self):
        text_batch, label_batch = super(TfIdfModel, self).validate_model()
        print(self.session.run(self.accuracy, feed_dict={self.x: text_batch,
                                    self.y_: label_batch}))      

class TfIdfConvModel(TFIDFModelBase):

    def __init__(self):
        super(TfIdfConvModel, self).__init__(10)
        self.num_steps  = 1000
        self.batch_size = 30

    def model_name(self):
        return "tfidf_conv"           

    @staticmethod
    def weight_variable(shape, name):
        initial = tf.truncated_normal(shape, stddev=0.1)
        return tf.Variable(initial, name=name)

    @staticmethod
    def bias_variable(shape, name):
        initial = tf.constant(0.1, shape=shape)
        return tf.Variable(initial, name=name)

    @staticmethod
    def conv2d(x, W, name):
        # Computes a 2-D convolution given 4-D input and filter tensors
        # strides = [batch, in_height, in_width, in_channels]
        return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME', name=name)

    @staticmethod
    def max_pool_2x2(x, name):
        # ksize: A list of ints that has length >= 4. The size of the window for each dimension of the input tensor.
        # strides: A list of ints that has length >= 4. The stride of the sliding window for each dimension of the input tensor.
        # It was [1, 2, 2, 1]
        return tf.nn.max_pool(x, ksize=[1, 1, 2, 1],
                            strides=[1, 1, 1, 1], padding='SAME', name=name)        

    def declare_tf(self):
        self.graph = tf.Graph()
        with self.graph.as_default():
            num_features = self.data.num_features()
            num_classes = self.data.num_classes
            # Some of authors call this variable "number of channels"
            num_features_to_consider = 32
            window_size = 5
            # We want to
            rehape_size = num_features
            # We have two layers. At each layer we cut the size twice 2*2 = 4.
            final_rehape_size = rehape_size 
            w_fc1_size = final_rehape_size * num_features_to_consider * 2

            print ("num_features: ", num_features)
            print ("rehape_size: ", rehape_size)

            self.x = tf.placeholder(tf.float32, [None, num_features], name="x")
            
            # Our real classes. It should have sites of self.data.num_features() x self.data.num_classes
            self.y_ = tf.placeholder(tf.float32, [None, num_classes], name="y_")

            ###########################
            # First convolusional layer
            ###########################
            self.W_conv1 = self.weight_variable([1, window_size, 1, num_features_to_consider], "W_conv1")
            self.b_conv1 = self.bias_variable([num_features_to_consider], "b_conv1")
            
            self.x_image = tf.reshape(self.x, [-1, 1, rehape_size, 1], name="x_image")

            self.h_conv1 = tf.nn.relu(self.conv2d(self.x_image, self.W_conv1, name="conv2d") + self.b_conv1)
            self.h_pool1 = self.max_pool_2x2(self.h_conv1, "h_pool1")

            ###########################
            # Second layer
            ###########################
            self.W_conv2 = self.weight_variable([1, window_size, num_features_to_consider, num_features_to_consider * 2], "W_conv2")
            self.b_conv2 = self.bias_variable([num_features_to_consider * 2], "b_conv2")

            self.h_conv2 = tf.nn.relu(self.conv2d(self.h_pool1, self.W_conv2, name="h_conv2") + self.b_conv2)
            self.h_pool2 = self.max_pool_2x2(self.h_conv2, "h_pool2")

            ###########################
            # Densely Connected Layer
            ###########################
            self.W_fc1 = self.weight_variable([w_fc1_size, 1024], name="W_fc1")
            self.b_fc1 = self.bias_variable([1024], name="b_fc1")

            self.h_pool2_flat = tf.reshape(self.h_pool2, [-1, w_fc1_size], name="h_pool2_flat")
            self.h_fc1 = tf.nn.relu(tf.matmul(self.h_pool2_flat, self.W_fc1) + self.b_fc1, name="h_fc1")

            ###########################
            # Droupupt
            ###########################
            self.keep_prob = tf.placeholder(tf.float32, name="keep_prob")
            self.h_fc1_drop = tf.nn.dropout(self.h_fc1, self.keep_prob, name="h_fc1_drop")

            ###########################
            # Readout layer
            ###########################
            self.W_fc2 = self.weight_variable([1024, num_classes], "W_fc2")
            self.b_fc2 = self.bias_variable([num_classes], "b_fc2")

            self.y_conv = tf.add(tf.matmul(self.h_fc1_drop, self.W_fc2), self.b_fc2, name="y_conv")

            ###########################
            # Train & Test
            ###########################
            self.cross_entropy = tf.reduce_mean(
                    tf.nn.softmax_cross_entropy_with_logits(labels=self.y_, logits=self.y_conv))
            self.train_step = tf.train.AdamOptimizer(1e-4).minimize(self.cross_entropy)
            
            self.correct_prediction = tf.equal(tf.argmax(self.y_conv,1), tf.argmax(self.y_,1), name="correct_prediction")
            self.accuracy = tf.reduce_mean(tf.cast(self.correct_prediction, tf.float32), name="accuracy")

            self.saver = tf.train.Saver(tf.global_variables())

    def train(self):
        self.declare_tf()
        with self.graph.as_default():
            init = tf.global_variables_initializer()
        self.session = tf.InteractiveSession(graph=self.graph)
        init.run()

        for step in range(self.num_steps):
            if (step % 100) == 0:
                print  ("Step: ", step) 
            text_batch, label_batch  = self.data.get_batch(self.batch_size)

            self.session.run(self.train_step, feed_dict={self.x: text_batch, self.y_: label_batch, self.keep_prob: 0.5})

        saving_path = self.saver.save(self.session, self.dump_filename)
        TFModel.create_one(self.model_name(), saving_path)    
        
        print ("Saved as ", saving_path)

    def validate_model(self):
        text_batch, label_batch = super(TfIdfConvModel, self).validate_model()

        print(self.session.run(self.accuracy, feed_dict={self.x: text_batch,
                                    self.y_: label_batch, self.keep_prob: 1.0}))

    def validate_get_class(self):
        documents = SourceData.test_data(10, True)
        print ("---------------Test negative----------------")
        for document in documents:
            result = self.get_class(document.body)
            print("IsPositive: ", result, ", document: ", document.body[:50])

        print ("---------------Test positive----------------")
        documents = SourceData.test_data(50)
        for document in documents:
            result = self.get_class(document.body)
            print("IsPositive: ", result, ", document: ", document.body[:50])


    def get_class(self, document):
        texts = list()
        processed_document = tf.compat.as_str(process_text(document, True, 2))
        texts.append(processed_document)
        sparse_tfidf_texts = self.data.tfidf.transform(texts)

        return self.session.run(tf.argmax(self.y_conv,1), feed_dict={self.x: sparse_tfidf_texts[0].todense(), self.keep_prob: 1.0})