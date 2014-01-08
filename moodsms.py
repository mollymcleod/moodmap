import os, urllib2
import json
import re
from pprint import pprint
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

@app.route('/<username_url>')
def calendar(username_url):
  u = User.query.filter_by(username_url = username_url).first_or_404()
  return render_template('calendar.html', user = u)

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')
  u = get_or_create_user(from_number, msg)

  # add element
  if valid_message(msg):
    datum = {'date' : format_datetime(datetime.now(), 'YYYY-MM-DD'),
            'mood': msg[0],
            'note' : msg}
    u.add_datum(datum)
    db.session.add(u)
    db.session.commit()
    return msg
  else:
    return "invalid msg"

# Models
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username_url = db.Column(db.String(80), unique=True)
  username = db.Column(db.String(80))
  phone_number = db.Column(db.String(20), unique=True)
  data = db.Column(db.Text())
  
  def __init__(self, phone_number, username, data = None):
    self.phone_number = phone_number
    self.username = username
    self.username_url = self.username_to_url(username)
    self.data = data

  def username_to_url(self, username):
    url = re.sub('[!@#$]', '', username)
    url = url.strip()
    url = url.replace(" ","-")
    return url

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

  def to_dict(self):
    user_dict = self.__dict__
    try:
      del user_dict['_sa_instance_state']
    except KeyError:
      pass
    return user_dict

  @classmethod
  def users_to_json_string(cls):
    user_dicts = []
    users = cls.query.all()
    for u in users:
      user_dicts.append(u.to_dict())
    return json.dumps(user_dicts)

  @classmethod
  def users_to_file(cls, filepath = None):
    users_string = cls.users_to_json_string()
    
    if filepath is None:
      timestamp = format_datetime(datetime.now(), 'YYYY-MM-DD-HH')
      filepath = 'data/%s-data.txt' % timestamp
    
    f = open(filepath, 'w')
    f.write(users_string)
    f.close()
    return filepath

  @classmethod
  def load_users_from_file(cls, filepath):
    users_string=open(filepath).read()
    users = json.loads(users_string)
    
    new_users = []
    error_count = 0
    for u in users:
      try:
        new_u = User(phone_number = u['phone_number'],
                    username = u['username'],
                    data = u.get('data'))
        db.session.add(new_u)
        new_users.append(new_u)
      except Exception:
        error_count += 1
    
    db.session.commit()
    return new_users, error_count

# Utils
def get_or_create_user(phone_number, username = None):
  u = User.query.filter_by(phone_number = phone_number).first()
  if u:
    return u
  else:
    u = User(phone_number = phone_number, username = username)
    db.session.add(u)
    welcome = "Welcome! Reply with 1 (terrible) to 5 (awesome) + a note about your day. You can see your mood map at http://mood-sms.herokuapp.com/%s" % u.phone_number
    send_message(u.phone_number, welcome)
    return u

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