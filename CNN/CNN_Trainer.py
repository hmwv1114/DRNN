# -*- coding: utf-8 -*-
'''
Created on 2015.4.12

@author: Yikang
'''

import numpy as np

import cPickle

import time, os

os.environ['MKL_NUM_THREADS'] = '1'

from CNN import CNN

max_length = 60

fixL = False

from multiprocessing import Pool, cpu_count

import gensim.models.word2vec as word2vec

def evaluate(args):
    model, sentences = args
    dpp = 0.0
    for n, x, y in sentences:
        predict = model.caculate(x)
        cross_entropy = -(y * np.log(predict[1]) + (1-y) * np.log(predict[0]))
        if predict[y] > 0.5:
            p = 1.0
        else:
            p = 0.0
        dpp += p
      
        print n, predict, p, cross_entropy
       
    return dpp/len(sentences)

def pv(args):
    model, sentences = args
    gps = []
    for param in model.params:
        gps.append(np.zeros_like(param, dtype=np.float32))
    dpp = 0.0
    for n, x, y in sentences:
        predict = model.caculate(x)
        cross_entropy = -(y * np.log(predict[1]) + (1-y) * np.log(predict[0]))
        if predict[y] > 0.5:
            p = 1.0
        else:
            p = 0.0
        dpp += p
        
        gparams_value = model.backprop(x, y)
        for i in range(len(gps)):
            gps[i] = gps[i] + gparams_value[i]
      
        print n, predict, p
       
    return (dpp/len(sentences), gps)

def predict(params, L, test_x, test_y, batch_size = 1000):
    rng = np.random.RandomState(1234)
    model = CNN(rng, L.shape[1], nword, Wc_values=params[0], Wh_values=params[1], Ws_values=params[2], L_values=L)
    
    n_train_batches = len(train_x) / batch_size
    n_per_process = batch_size / cpu_count()
    
    pool = Pool()
    
    differencelist = []
    n = 0
    for minibatch_index in xrange(n_train_batches):
        process_task = []
        count = 0
        for i in range(minibatch_index * batch_size, (minibatch_index + 1) * batch_size):
            n += 1
            
            if count == 0:
                sentences = []
                
            l = train_x[i].shape[0]
            if l < 2:
                continue
            sentences.append((n, test_x[i], test_y[i]))
            count += 1
            
            if count > n_per_process:
                process_task.append((model, sentences))
                count = 0
        process_task.append((model, sentences))
                
        results = pool.map(evaluate, process_task)
        for dpp in results:          
            differencelist.append(dpp)
    
    print np.mean(differencelist)
    

def train_DRNN(nword, train_x, train_y, test_x, test_y, max_length, 
               params=None, L = None, margin = 0.1, learning_rate=0.01, 
               L1_reg=0.00, L2_reg=0.0001, n_epochs=100, batch_size=500):
    rng = np.random.RandomState(1234)
        
    if params != None:
        model = CNN(rng, L.shape[1], nword, Wc_values=params[0], Wh_values=params[1], Ws_values=params[2], L_values=L)
    elif L != None:
        model = CNN(rng, L.shape[1], nword, L_values=L)
    else:
        model = CNN(rng, 100, nword)
    
    best_iter = 0
    test_score = 0.
    start_time = time.clock()

    n_train_batches = len(train_x) / batch_size
    n_per_process = batch_size / cpu_count()
    
    pool = Pool()
    
    epoch = 0
    average_diff = []
    logfille = open('training_log.txt', 'w')
    logfille.write(str(time.clock())+'\n')
    logfille.flush()
    while epoch < n_epochs:
        epoch = epoch + 1
        differencelist = []
        n = 0
        for minibatch_index in xrange(n_train_batches):
            process_task = []
            count = 0
            for i in range(minibatch_index * batch_size, (minibatch_index + 1) * batch_size):
                n += 1
                
                if count == 0:
                    sentences = []
                    
                l = train_x[i].shape[0]
                if l < 2:
                    continue
                sentences.append((n, train_x[i], train_y[i]))
                count += 1
                
                if count > n_per_process:
                    process_task.append((model, sentences))
                    count = 0
            process_task.append((model, sentences))
                    
            results = pool.map(pv, process_task)
            
            gps = []
            for param in model.params:
                gps.append(np.zeros_like(param, dtype=np.float32))
            for dpp, gparams_value in results:
                for i in range(len(gps)):
                    gps[i] = gps[i] + gparams_value[i]            
                differencelist.append(dpp)
                
            for i in range(len(gps)):
                model.params[i] += learning_rate * gps[i] / batch_size
        
        average_diff.append(np.mean(differencelist))
        
        output = open('params_epoch_'+str(epoch)+'_'+str(np.mean(differencelist))+'.pkl', 'w')
        cPickle.dump(model.params, output)
        output.close()
            
        logfille.write(str(time.clock())+'\n')
        logfille.write('epoch:' + str(epoch) + 'p0, p1 difference:' + str(np.mean(differencelist)) + '\n')
        logfille.flush()
    logfille.close()

if __name__ == '__main__':
    model = word2vec.Word2Vec.load('stanford_word_vector')
    nword = len(model.vocab.keys())
    L = model.syn0
    
    bmatfile = open('doc_binary_matrix_stanford.pkl', 'r')
    (train_x, train_y), (test_x, test_y) = cPickle.load(bmatfile)
    bmatfile.close()
    
    print train_x[0], train_y[0]
    
    params_file = open('params_epoch_18_0.653410628019.pkl','r')
    params = cPickle.load(params_file)
    params_file.close()
    
    train_DRNN(nword, train_x, train_y, test_x, test_y, max_length, L=L.astype(np.float32))
    
    #predict(params, L, test_x, test_y)
