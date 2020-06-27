import re 
import requests 
from bs4 import BeautifulSoup 
from urllib.request import urlopen
from flask import Flask, request, render_template 
app = Flask(__name__) 


@app.route('/') 
def hellohtml(): 
    return render_template("hello.html") 
@app.route('/method', methods=['GET', 'POST']) 
def method(): 
        num = request.form["num"] 
        #name = request.form["name"] 
        url = num
        res = requests.get(url)
        html = BeautifulSoup(res.content, "html.parser")
        
        html_title = html.find("title")
        
        html_body = html.find(attrs={'class':'mw-parser-output'})
        title = html_title.text 
        body = html_body.find('p').text
        print("title:", title) 
        print("body:", body)
        return title
        

    
if __name__ == '__main__': 
    app.run(debug=True)
    