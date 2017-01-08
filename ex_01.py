import os
import time
import gzip
import pickle

import numpy as np
import keras as K
import tensorflow as tf

from utils_mnist import load_mnist
from utils_mnist import build_mlp as MLP

from attacks import jsma


print('Loading mnist')
(X_train, y_train,
 X_test, y_test,
 X_val, y_val) = load_mnist(validation_split=0.1)

batch_size = 64
nb_sample = X_train.shape[0]
nb_batch = int(nb_sample / batch_size)
nb_epoch = 20

with tf.Session() as sess:
    K.backend.set_session(sess)

    x = tf.placeholder(tf.float32, shape=(None, 784))
    y = tf.placeholder(tf.float32, shape=(None, 10))

    print('Building model')
    model = MLP()
    ybar = model(x)

    acc = K.metrics.categorical_accuracy(y, ybar)
    loss = K.metrics.categorical_crossentropy(y, ybar)
    train_step = tf.train.AdamOptimizer().minimize(loss)

    target = tf.placeholder(tf.int32, shape=())
    x_adv = jsma(model, x, target, delta=1.)

    init = tf.global_variables_initializer()
    sess.run(init)

    info = 'Elapsed {0:.2f}s, loss {1:.4f}, acc {2:.4f}'

    print('Training')
    for epoch in range(nb_epoch):
        print('Epoch {0}/{1}'.format(epoch+1, nb_epoch))
        tick = time.time()
        for batch in range(nb_batch):
            print(' batch {0}/{1}' .format(batch+1, nb_batch),
                  end='\r')
            end = min(nb_sample, (batch+1)*batch_size)
            start = end - batch_size
            sess.run([train_step], feed_dict={
                x: X_train[start:end],
                y: y_train[start:end],
                K.backend.learning_phase(): 1})
        tock = time.time()
        accval, lossval = sess.run([acc, loss], feed_dict={
            x: X_val, y: y_val, K.backend.learning_phase(): 0})
        print(info.format(tock-tick, np.mean(lossval),
                          np.mean(accval)))

    print('Testing against original test data')
    tick = time.time()
    accval, lossval = sess.run([acc, loss], feed_dict={
        x: X_test, y: y_test, K.backend.learning_phase(): 0})
    tock = time.time()
    print(info.format(tock-tick, np.mean(lossval), np.mean(accval)))

    print('Construct adversarial images from blank images')
    blank = np.zeros((1, 784))
    digits = np.empty((10, 784))
    for i in range(10):
        tick = time.time()
        adv = sess.run(x_adv, feed_dict={
            x: blank, target: i, K.backend.learning_phase(): 0})
        digits[i] = adv.flatten()
        yval = sess.run(ybar, feed_dict={
            x: adv, K.backend.learning_phase(): 0})
        tock = time.time()
        print('Elapsed {0:.2f}s label {1} ({2:.2f})'
              .format(tock-tick, np.argmax(yval), np.max(yval)))

    os.makedirs('data', exist_ok=True)
    with gzip.open('data/digits.pkl.gz', 'wb') as w:
        pickle.dump(digits.tolist(), w)
