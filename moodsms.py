import os, urllib2
import gspread
from datetime import datetime
from twilio.rest import TwilioRestClient
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
  date = datetime.today()
  mood = msg[0]
  note = msg[2:]
  add_row([date, mood, note])
  return "added row"

# Utils
def send_reminder(phone_number):
  body = 'How was your day? Reply 1-5 and a note'
  send_message(phone_number, body)

def send_message(phone_number, body):
  account_sid = os.environ['ACCOUNT_SID']
  auth_token = os.environ['AUTH_TOKEN']
  twilio_number = os.environ['TWILIO_NUMBER']
  client = TwilioRestClient(account_sid, auth_token)
  client.sms.messages.create(to=phone_number, from_=twilio_number, body=body[:160])

def add_row(row):
  if len(row) == 3:
    next_row = len(wks.col_values(1)) + 1
    for index, c in enumerate(row):
      wks.update_cell(next_row, index+1, c)