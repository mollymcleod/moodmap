import os, urllib2
import json
from twilio.rest import TwilioRestClient
from datetime import datetime
from babel.dates import format_datetime
from flask import Flask, request, render_template, redirect
from flask.ext.sqlalchemy import SQLAlchemy

# Setup
app = Flask(__name__)
app.config['DEBUG'] = os.environ['DEBUG']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

# Routes
@app.errorhandler(404)
def not_found(error):
    return render_template('error.html'), 404

@app.teardown_request
def shutdown_session(exception=None):
  try:
    db.session.commit()
    db.session.remove()
  except:
    db.session.rollback()

@app.route('/')
def index():
  users = User.query.all()
  return render_template('index.html', users = users)

@app.route('/<phone_number>')
def calendar(phone_number):
  u = User.query.filter_by(phone_number = phone_number).first_or_404()
  return render_template('calendar.html', user = u)

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')
  u = get_or_create_user(from_number)

  # add element
  if valid_message(msg):
    datum = {'date' : format_datetime(datetime.now(), 'YYYY-MM-DD'),
            'mood': msg[0],
            'note' : msg}
    u.add_datum(datum)
    db.session.add(u)
    db.session.commit()
    return msg
  # else:
  #   correction = "Reply with a number 1-5 + a note, like this: '5. Great day hike in Muir Woods!'"
  #   return send_message(u.phone_number, correction)

# Models
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  phone_number = db.Column(db.String(20), unique=True)
  data = db.Column(db.Text())
  
  def __init__(self, phone_number, data = None):
    self.phone_number = phone_number
    self.data = data

  def save_json_as_text(self, json_data):
    text_data = json.dumps(json_data)
    self.data = text_data

  def get_data_as_json(self):
    if self.data:
      return json.loads(self.data)
    else:
      return {}

  def add_datum(self, datum):
    data = self.get_data_as_json()
    data[datum['date']] = {'mood' : datum['mood'], 'note' : datum['note']}
    self.save_json_as_text(data)

# Utils
def get_or_create_user(phone_number):
  u = User.query.filter_by(phone_number = phone_number).first()
  if u:
    return u
  else:
    u = User(phone_number = phone_number)
    welcome = "Welcome! Reply with 1 (terrible) to 5 (awesome) + a note about your day. You can see your mood map at www.mood-sms.herokuapp.com/%s" % u.phone_number
    return send_message(u.phone_number, welcome)

def send_message(phone_number, body):
  account_sid = os.environ['TWILIO_SID']
  auth_token = os.environ['TWILIO_AUTH']
  twilio_number = os.environ['TWILIO_NUM']
  client = TwilioRestClient(account_sid, auth_token)
  client.sms.messages.create(to=phone_number, from_=twilio_number, body=body[:160])
  return body

def valid_message(msg):
  if msg and msg[0].isdigit() and int(msg[0]) in range(1,6):
    return True
  else:
    return False