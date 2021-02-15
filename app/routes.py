from flask import render_template, request, redirect, session, Markup
from . import application
import pandas as pd
from urllib.request import urlopen
from app.centrality import Centrality
from app.svg_parse import SVGParse
import requests
import json
import urllib
import tempfile
import os
import uuid


@application.route('/')
@application.route('/index')
def index():
    return render_template('index.html')



@application.route('/index', methods=['POST'])
def my_form_post():
    iat_mode = 'false'
    text = request.form['text']
    session['text_var'] = text
    return redirect('/results')
