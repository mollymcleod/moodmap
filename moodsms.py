import os, urllib2
import gspread
from datetime import datetime
from babel.dates import format_datetime
from flask import Flask, request, render_template, redirect

# Setup
app = Flask(__name__)
app.config['DEBUG'] = os.environ['DEBUG']

# Login and get worksheet
doc_name = os.environ['GDOC_TITLE']
username = os.environ['GOOGLE_USERNAME']
password = os.environ['GOOGLE_PASSWORD']
gdoc_url = 'https://docs.google.com/spreadsheet/pub?key=%s&single=true&gid=0&output=csv' % os.environ['GDOC_KEY']
gc = gspread.login(username, password)
wks = gc.open(doc_name).sheet1

# Routes
@app.route('/')
def index():
  return render_template('calendar.html', gdoc_url=gdoc_url)

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')

  # create next row
  date = format_datetime(datetime.now(), 'YYYY-MM-DD')
  mood = msg[0]
  note = msg[2:]
  add_row([date, mood, note])
  return "added row"

# Utils
def add_row(row):
  if len(row) == 3:
    next_row = len(wks.col_values(1)) + 1
    for index, c in enumerate(row):
      wks.update_cell(next_row, index+1, c)