#!/usr/bin/env python

import numpy as np
import random

from utils.gradcheck import gradcheck_naive
from utils.utils import normalizeRows, softmax
from utils.sanity_checks import *
import pdb


def sigmoid(x):
    """
    Compute the sigmoid function for the input here.
    Arguments:
    x -- A scalar or numpy array.
    Return:
    s -- sigmoid(x)
    """
    s = np.exp(x)/(1+np.exp(x)) 
    return s


def naiveSoftmaxLossAndGradient(
        centerWordVec,
        outsideWordIdx,
        outsideVectors,
        dataset
):
    """ Naive Softmax loss & gradient function for word2vec models

    Implement the naive softmax loss and gradients between a center word's 
    embedding and an outside word's embedding. This will be the building block
    for our word2vec models.

    Arguments:
    centerWordVec -- numpy ndarray, center word's embedding
                    (v_c in the pdf handout)
    outsideWordIdx -- integer, the index of the outside word
                    (o of u_o in the pdf handout)
    outsideVectors -- outside vectors (rows of matrix) for all words in vocab
                      (U in the pdf handout)
    dataset -- needed for negative sampling, unused here.

    Return:
    loss -- naive softmax loss
    gradCenterVec -- the gradient with respect to the center word vector
                     (dJ / dv_c in the pdf handout)
    gradOutsideVecs -- the gradient with respect to all the outside word vectors
                    (dJ / dU)
    """
    
    ### YOUR CODE HERE
    #calculating loss
    exp_all = np.exp(np.dot(centerWordVec, outsideVectors.transpose()))
    loss_nume = exp_all[outsideWordIdx]
    loss_denom = np.sum(exp_all)
    loss = -1*np.log(np.divide(loss_nume, loss_denom))

    # calculating gradCenterVec 
    u_o = outsideVectors[outsideWordIdx,:]
    second_term =  np.multiply(np.divide(exp_all, loss_denom), outsideVectors.transpose())
    gradCenterVec = -1*u_o + second_term.sum(axis=1)

    #calculating gradOutsideVecs
    centerWordVec_arr = np.array([centerWordVec]*exp_all.shape[0]).transpose()
    gradOutsideVecs = np.multiply(np.divide(exp_all, loss_denom),centerWordVec_arr)
    gradOutsideVecs[:,outsideWordIdx] += -1*centerWordVec
    gradOutsideVecs = gradOutsideVecs.transpose()
    ### END YOUR CODE

    return loss, gradCenterVec, gradOutsideVecs


def getNegativeSamples(outsideWordIdx, dataset, K):
    """ Samples K indexes which are not the outsideWordIdx """

    negSampleWordIndices = [None] * K
    for k in range(K):
        newidx = dataset.sampleTokenIdx()
        while newidx == outsideWordIdx:
            newidx = dataset.sampleTokenIdx()
        negSampleWordIndices[k] = newidx
    return negSampleWordIndices


def negSamplingLossAndGradient(
        centerWordVec,
        outsideWordIdx,
        outsideVectors,
        dataset,
        K=10
):
    """ Negative sampling loss function for word2vec models

    Arguments/Return Specifications: same as naiveSoftmaxLossAndGradient
    K is the number of negative samples to take.

    """

    negSampleWordIndices = getNegativeSamples(outsideWordIdx, dataset, K)
    indices = [outsideWordIdx] + negSampleWordIndices

    gradCenterVec = np.zeros(centerWordVec.shape)
    gradOutsideVecs = np.zeros(outsideVectors.shape)

    labels = np.array([1] + [-1 for k in range(K)])
    vecs = outsideVectors[indices, :]

    t = sigmoid(vecs.dot(centerWordVec) * labels)
    loss = -np.sum(np.log(t))

    delta = labels * (t - 1)
    gradCenterVec = delta.reshape((1, K + 1)).dot(vecs).flatten()
    gradOutsideVecsTemp = delta.reshape((K + 1, 1)).dot(centerWordVec.reshape(
        (1, centerWordVec.shape[0])))
    for k in range(K + 1):
        gradOutsideVecs[indices[k]] += gradOutsideVecsTemp[k, :]

    return loss, gradCenterVec, gradOutsideVecs


def skipgram(currentCenterWord, windowSize, outsideWords, word2Ind,
             centerWordVectors, outsideVectors, dataset,
             word2vecLossAndGradient=negSamplingLossAndGradient):
    """ Skip-gram model in word2vec

    Implement the skip-gram model in this function.

    Arguments:
    currentCenterWord -- a string of the current center word
    windowSize -- integer, context window size
    outsideWords -- list of no more than 2*windowSize strings, the outside words
    word2Ind -- a dictionary that maps words to their indices in
              the word vector list
    centerWordVectors -- center word vectors (as rows) for all words in vocab
                        (V in pdf handout)
    outsideVectors -- outside word vectors (as rows) for all words in vocab
                    (U in pdf handout)
    word2vecLossAndGradient -- the loss and gradient function for
                               a prediction vector given the outsideWordIdx
                               word vectors, could be one of the two
                               loss functions you implemented above.

    Return:
    loss -- the loss function value for the skip-gram model
            (J in the pdf handout)
    gradCenterVecs -- the gradient with respect to the center word vectors
            (dJ / dV in the pdf handout)
    gradOutsideVectors -- the gradient with respect to the outside word vectors
                        (dJ / dU in the pdf handout)
    """

    loss = 0.0
    gradCenterVecs = np.zeros(centerWordVectors.shape)
    gradOutsideVectors = np.zeros(outsideVectors.shape)

    ### YOUR CODE HERE
    centerWordIndex = word2Ind[currentCenterWord]
    centerWordVec = centerWordVectors[centerWordIndex]
    for word in outsideWords:
        word_index = word2Ind[word]
        loss_current, gradc, grado = word2vecLossAndGradient(
            centerWordVec=centerWordVec,
            outsideWordIdx=word_index,
            outsideVectors=outsideVectors,
            dataset=dataset
        )
        loss += loss_current
        gradCenterVecs[centerWordIndex] += gradc
        gradOutsideVectors += grado

    return loss, gradCenterVecs, gradOutsideVectors


def word2vec_sgd_wrapper(word2vecModel, word2Ind, wordVectors, dataset,
                         windowSize,
                         word2vecLossAndGradient=negSamplingLossAndGradient):
    batchsize = 50
    loss = 0.0
    grad = np.zeros(wordVectors.shape)
    N = wordVectors.shape[0]
    centerWordVectors = wordVectors[:int(N / 2), :]
    outsideVectors = wordVectors[int(N / 2):, :]
    for i in range(batchsize):
        windowSize1 = random.randint(1, windowSize)
        centerWord, context = dataset.getRandomContext(windowSize1)

        c, gin, gout = word2vecModel(
            centerWord, windowSize1, context, word2Ind, centerWordVectors,
            outsideVectors, dataset, word2vecLossAndGradient
        )
        loss += c / batchsize
        grad[:int(N / 2), :] += gin / batchsize
        grad[int(N / 2):, :] += gout / batchsize

    return loss, grad


#############################################
# Testing functions below. DO NOT MODIFY!   #
#############################################


def test_naiveSoftmaxLossAndGradient():
    print("\n\n\t\t\tNaiveSoftmaxLossAndGradient\t\t\t")

    dataset, dummy_vectors, dummy_tokens = dummy()

    print("\nYour Result:")
    loss, dj_dv, dj_du = naiveSoftmaxLossAndGradient(
        inputs['test_naivesoftmax']['centerWordVec'],
        inputs['test_naivesoftmax']['outsideWordIdx'],
        inputs['test_naivesoftmax']['outsideVectors'],
        dataset
    )

    print(
        "Loss: {}\nGradient wrt Center Vector (dJ/dV):\n {}\nGradient wrt Outside Vectors (dJ/dU):\n {}\n".format(loss,
                                                                                                                  dj_dv,
                                                                                                                  dj_du))

    print("Expected Result: Value should approximate these:")
    print(
        "Loss: {}\nGradient wrt Center Vectors(dJ/dV):\n {}\nGradient wrt Outside Vectors (dJ/dU):\n {}\n".format(
            outputs['test_naivesoftmax']['loss'],
            outputs['test_naivesoftmax']['dj_dvc'],
            outputs['test_naivesoftmax']['dj_du']))


def test_sigmoid():
    print("\n\n\t\t\ttest softmax\t\t\t")

    x = inputs['test_sigmoid']['x']
    s = sigmoid(x)

    print("\nYour Result:")
    print(s)
    print("Expected Result: Value should approximate these:")
    print(outputs['test_sigmoid']['s'])


def test_word2vec():
    """ Test the two word2vec implementations, before running on Stanford Sentiment Treebank """
    dataset, dummy_vectors, dummy_tokens = dummy()

    print("==== Gradient check for skip-gram with naiveSoftmaxLossAndGradient ====")
    gradcheck_naive(lambda vec: word2vec_sgd_wrapper(
        skipgram, dummy_tokens, vec, dataset, 5, negSamplingLossAndGradient),
                    dummy_vectors, "naiveSoftmaxLossAndGradient Gradient")

    print("\n\n\t\t\tSkip-Gram with naiveSoftmaxLossAndGradient\t\t\t")

    print("\nYour Result:")
    loss, dj_dv, dj_du = skipgram(inputs['test_word2vec']['currentCenterWord'], inputs['test_word2vec']['windowSize'],
                                  inputs['test_word2vec']['outsideWords'],
                                  dummy_tokens, dummy_vectors[:5, :], dummy_vectors[5:, :], dataset,
                                  naiveSoftmaxLossAndGradient)
    print(
        "Loss: {}\nGradient wrt Center Vectors (dJ/dV):\n {}\nGradient wrt Outside Vectors (dJ/dU):\n {}\n".format(loss,
                                                                                                                   dj_dv,
                                                                                                                   dj_du))

    print("Expected Result: Value should approximate these:")
    print(
        "Loss: {}\nGradient wrt Center Vectors (dJ/dV):\n {}\nGradient wrt Outside Vectors (dJ/dU):\n {}\n".format(
            outputs['test_word2vec']['loss'],
            outputs['test_word2vec']['dj_dv'],
            outputs['test_word2vec']['dj_du']))


if __name__ == "__main__":
    test_word2vec()
    test_naiveSoftmaxLossAndGradient()
    test_sigmoid()
