#!/usr/bin/python
#-*- coding: utf-8 -*-
import argparse
import subprocess
from flask import Flask, jsonify, request, render_template
import re
import requests
from bs4 import BeautifulSoup
import operator
import json
import ast
import operator
import numpy
from nltk import word_tokenize
import math
from nltk.corpus import stopwords
import timeit
from requests.exceptions import ConnectionError
from elasticsearch import Elasticsearch
from werkzeug.utils import secure_filename
url_list = []
word_d_list = []
tmp=1
host="127.0.0.1"
port="5000"

def whole_word_count(i): #i번째 url의 전체 단어수 return
    count = sum(word_d_list[i].values())
    return count

#COSINE SIMILARITY#
def make_vector(i): #i번째 url
    vector = {} # word 빈도수 딕셔너리
    for word_d in word_d_list:
        for key in word_d.keys():
            if key not in vector.keys():
                vector[key] = 0

    for key in word_d_list[i].keys():
        vector[key] = word_d_list[i][key]

    vector_list = []
    for val in vector.values():
        vector_list.append(val)
    return vector_list

def calculate_cossimil(): #cosine similarity Top3 출력
    cossimil_dic = {}
    for i in range(0, len(url_list)):
        v1 = make_vector(i)
        for j in range(i+1, len(url_list)):
            v2 = make_vector(j)
            dotpro = numpy.dot(v1,v2)
            cossimil = dotpro / numpy.linalg.norm(v1) * numpy.linalg.norm(v2)
            key = str(i) + '&' + str(j)
            cossimil_dic[key] = cossimil
    cossimil_dic = sorted(cossimil_dic.items(), key=operator.itemgetter(1), reverse=True) #내림차순 정렬

    print_dic = {}
    if len(cossimil_dic)>=3:
        for i in range(0,3):
            print_dic[i] = cossimil_dic[i]
        return print_dic

    else:
        for i in range(0,len(cossimil_dic)):
            print_dic[i] = cossimil_dic[i]
        return print_dic

#TF-IDF#
def calculate_tf(word_dic):
    tf_d = {}
    for word in word_dic.keys():
        tf_d[word] = word_dic[word]/float(sum(word_dic.values()))
    return tf_d

def calculate_idf():
    Dval = len(url_list)
    print ("url_list")
    print (url_list)
    idf_d = {}
    for word_d in word_d_list:
        word_d = ast.literal_eval(json.dumps(word_d))
        for word in word_d.keys():
            cnt = 0
            for i in range(0,Dval):
                if word in word_d_list[i].keys():
                    cnt += 1
            if word not in idf_d.keys():
                idf_d[word] = math.log10(Dval/float(cnt))
    return idf_d

def calculate_tfidf():
    tfidf_dic = {}
    idf_d = calculate_idf()
    for i in range(0,len(url_list)):
        tf_d = calculate_tf(word_d_list[i])
        for word,tfval in tf_d.items():
            tfidf_dic[word] = tfval*idf_d[word]
    tfidf_dic = sorted(tfidf_dic.items(), key=operator.itemgetter(1), reverse=True) #내림차순
    print_dic ={}
    for i in range(0,10):
        print_dic[i] = tfidf_dic[i]
    return print_dic

app = Flask(__name__)

@app.route('/single', methods=['POST', 'GET'])
def name2_check():
        if request.method == 'POST':
            start = timeit.default_timer() #시간측정 start
            a = request.form['single']
            global word_d_list
            global url_list
            global tmp
            repeat = []
            denied = []
            checked = []
            count = 0
            es = Elasticsearch(host="127.0.0.1",port="5000",timeout=30)

            while True:
                try:
                    docs = es.search(index='url')
                    url_list=[]
                    word_d_list=[]
                    if docs['hits']['total'] > 0:
                        for doc in docs['hits']['hits']:
                            url_list.append(doc['_source'].get('url'))
                            checked.append(doc['_source'].get('url'))
                            word_d_list.append(doc['_source'].get('wordfreq'))
                            count+=1
                            print ("읽어옴")
                            print (doc['_source'].get('url'), count)
                    break
                except Exception as e:
                    print ("exception error1")
                    break

            size = len(url_list)
            url = a+"\n"

            print (size)
            print (count)
            print (url_list)

            if( url in url_list):
                print ("중복")
                return "중복된 사이트 입니다. ->" + str(url)
            else:
                checked.append(url)

            try:
                res = requests.get(url,timeout=5)
            except ConnectionError as e:
                return "유효 하지 않은 사이트"

            res = requests.get(url)
            html = BeautifulSoup(res.content, "html.parser")
            html_body = html.find('body')
            string = html_body.text

            word_d={}
            for s in re.split('[.,}{? \s:;)(")]', string):
                if( len(s)>0 ):
                    if( s not in word_d):
                        word_d[s] = 1
                    else :
                        word_d[s] += 1

            word_d = ast.literal_eval(json.dumps(word_d))
            for sword in stopwords.words("english"):
                if( sword in word_d ):
                    word_d.pop(sword)
            print ("word_d")
            print (word_d)
            word_d_list.append(word_d)

            print  ("word_d_list"+str(len(word_d_list)))
            print (word_d_list)
            url_list.append(url)

            if( len(url_list) < 2 ):
                word_d_list  = ast.literal_eval(json.dumps(word_d_list))
                e1={
                    "url": url_list[0],
                    "wordfreq": word_d_list[0]
                }
                es.index(index='url', doc_type='doc', id=1, body=e1)
                print (url_list[0])
                return "저장된 url이 하나입니다.(비교 불가)"

            tempdiction=calculate_tfidf()
            tempdiction2=calculate_cossimil()
            e1={
                "url":url,
                "wordfreq":word_d
            }
            es.index(index='url', doc_type='doc',id = count+1, body=e1)
            e2={
                "url_list":url_list,
                "cossimil":str(tempdiction2),
                "tf_idf":str(tempdiction)
            }
            es.index(index='result',doc_type='doc',id=tmp,body=e2)
            tmp+=1
            stop = timeit.default_timer() #시간측정 stop

            str1 = str(url_list)
            
            whole_count = {}
            i=0
            for url in url_list:
                whole_count[url] = whole_word_count(i)
                i=i+1 
            
            return render_template("result.html",whole_count = whole_count) + "complete"+"<br> tf-idf:"+ str(tempdiction)+"<br> cosine similarity:"+str(tempdiction2) + "<br>run time: " +str(stop-start) + "<br> not accesible url : "

@app.route('/double', methods=['POST', 'GET'])
def name3_check():
        if request.method == 'POST':
            start = timeit.default_timer() #시간측정 start
            global word_d_list
            global url_list
            global tmp
            count = 0
            checked = []
            es = Elasticsearch(host="127.0.0.1",port="5000",timeout=30)
            while True:
                try:
                    docs = es.search(index="url")
                    url_list=[]
                    word_d_list=[]
                    if docs['hits']['total'] > 0:
                        for doc in docs['hits']['hits']:
                            url_list.append(doc['_source'].get('url'))
                            checked.append(doc['_source'].get('url'))
                            word_d_list.append(doc['_source'].get('wordfreq'))
                            count+=1
                    break
                except Exception as e:
                    print ("exception error2")
                    break
            print (str(len(url_list)))
            b = request.files['double']
            b.save(secure_filename(b.filename))
            urlbox=[]
            word_d={}
            i=1
            repeat = []
            denied = []

            fname = b.filename
            with open(fname,"r") as f:
                lines =f.readlines()
                for ln in lines:
                    url = ln
                    print (i)
                    i+=1
                    if( ln in urlbox or ln in url_list):
                        print ("중복 :"+ln)
                        repeat.append(ln)
                        continue

                    try:
                        res = requests.get(url,timeout=5)
                    except ConnectionError as e:
                        print ("유효 하지 않은 사이트")
                        denied.append(url)
                        continue

                    html = BeautifulSoup(res.content, "html.parser")
                    html_body = html.find('body')
                    string = html_body.text
                    for s in re.split('[.,}{? \s:;)/\(")]', string):
                        if( len(s)>0 ):
                            if( s not in word_d):
                                word_d[s] = 1
                            else :
                                word_d[s] += 1

                    word_d = ast.literal_eval(json.dumps(word_d))
                    for sword in stopwords.words("english"):
                        if( sword in word_d ):
                            word_d.pop(sword)

                    word_d_list.append(word_d)
                    url_list.append(url)
                    checked.append(url)
                    urlbox.append(ln)

            if( len(url_list) < 2 ):
                word_d_list  = ast.literal_eval(json.dumps(word_d_list))
                e1={
                    "url": url_list[0],
                    "wordfreq": word_d_list[0]
                }
                print (i)
                es.index(index='url', doc_type='doc', id=1, body=e1)
                print (url_list[0])
                return "저장된 url이 하나입니다.(비교 불가)"

            if ( len(word_d_list) == count ):
                tempdiction=calculate_tfidf()
                tempdiction2=calculate_cossimil()
                return "분석 할게 없음 모두 중복" + str(url_list) + "<br> tf-idf:"+ str(tempdiction)+"<br> cosine similarity:"+str(tempdiction2)

            word_d_list  = ast.literal_eval(json.dumps(word_d_list))
            print ("계산시작")
            tempdiction=calculate_tfidf()
            tempdiction2=calculate_cossimil()
            print ("계산 종료" + str(len(url_list)))
            # elsatic search에 입력
            for i in range(count,len(url_list)):
                e1={
                    "url": url_list[i],
                    "wordfreq": word_d_list[i]
                }
                print (i)
                es.index(index='url', doc_type='doc', id=i+1, body=e1)
                print (url_list[i])

            e2={
                "url_list":url_list,
                "cossimil":str(tempdiction2),
                "tf_idf":str(tempdiction)
            }
            es.index(index='result',doc_type='doc',id=tmp,body=e2)
            tmp+=1
            stop = timeit.default_timer() #시간측정 stop
            str1 = str(repeat)
            str2 = str(denied)
            str3 = str(checked)

            whole_count = {}
            i=0
            for url in url_list:
                whole_count[url] = whole_word_count(i)
                i=i+1 

            return  render_template("result.html",whole_count = whole_count+"complete"+"<br> tf-idf:"+ str(tempdiction)+"<br> cosine similarity:"+str(tempdiction2) + "<br>run time : " +str(stop-start)+"<br> duplicated url : "+str1+ "<br> not accesible url : "+str2)

"<button onclick=\"window.open('/test','window_name','width=100,height=100');\">button</button>"

@app.route('/', methods=['GET'])
def hello_test():
        return "<html lang=\"en\"><head><meta charset=\"UTF-8\"><title>Post</title></head><body><form action=\"/single\" method=\"post\"><p>URL<input type=\"text\"name=\"single\"></p><input type=\"submit\" value=\"Analyze\"></form></body></html>  <html><body><form action=\"/double\" method = \"POST\" enctype = \"multipart/form-data\"><input type = \"file\" name = \"double\" /><input type = \"submit\"/></form></body></html>  " 

if __name__ == '__main__':
    # try:
    #     parser = argparse.ArgumentParser(description="")
    #     parser.add_argument('--listen-port',  type=str, required=True, help='REST service listen port')
    #     args = parser.parse_args()
    #     listen_port = args.listen_port
    # except Exception as e:
    #     print('Error: %s' % str(e))

    # ipaddr=subprocess.getoutput("hostname -I").split()[0]
    # print ("Starting the service with ip_addr="+ipaddr)
    # app.run(debug=False,host=ipaddr,port=int(listen_port))
    app.run(debug=False)
