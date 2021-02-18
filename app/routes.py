from flask import render_template, request, redirect, session, Markup
from . import app
import pandas as pd
from urllib.request import urlopen
import requests
import json
import urllib
import tempfile
import os
import uuid
from app.centrality import Centrality
from app.SentenceSimilarity import SentenceSimilarity
from itertools import combinations
import datetime
import copy
import re
from glob import glob
import spacy
import sys
import statistics


@app.route('/')
@app.route('/index')
def index():
    return redirect('/form')


@app.route('/form')
def my_form():
    return render_template('index.html')

@app.route('/form', methods=['POST'])
def my_form_post():
    print('GOT HERE')
    iat_mode = 'false'
    text = request.form['text']
    session['text_var'] = text
    return redirect('/results')

@app.route('/results')
def render_text():
    text = session.get('text_var', None)

    print(text)

    return render_template('results.html')
