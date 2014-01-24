import os, urllib2
import json
import re
import operator
from twilio.rest import TwilioRestClient
from datetime import datetime
from babel.dates import format_datetime
from flask import Flask, request, render_template, redirect, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

# Setup
app = Flask(__name__)
app.config['DEBUG'] = os.environ['DEBUG']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

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
  users_json = [u.to_json() for u in users]
  return render_template('index.html', users = users, users_json = users_json)

@app.route('/users')
def users():
  users = User.query.all()
  return render_template('users.html', users = users)

@app.route('/<username_url>')
def calendar(username_url):
  u = User.query.filter_by(username_url = username_url).first_or_404()
  return render_template('calendar.html', user = u)

@app.route('/invite/<phone_number>')
def invite(phone_number = None):
  u = User.query.filter_by(phone_number = phone_number).first()
  if phone_number is None:
    return 'What phone # do you want to invite?'
  elif u:
    return "Looks like they already joined!"
  else:
    return send_message(phone_number, render_template('invite.html'))

@app.route('/<username_url>/json')
def json_data(username_url):
  u = User.query.filter_by(username_url = username_url).first_or_404()
  return u.data if u.data else 'no data here...'

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')
  u = get_or_create_user(from_number, msg)

  # add element
  if valid_message(msg):
    entry = Entry(msg[0], msg)
    u.entries.append(entry)
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
  entries = db.relationship('Entry', backref='user', lazy='dynamic')
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
    url = url.lower()
    return url

  def get_data_as_json(self):
    if self.data:
      return json.loads(self.data)
    else:
      return {}

  def to_dict(self):
    user_dict = dict(self.__dict__)
    try:
      del user_dict['_sa_instance_state']
    except Exception:
      pass
    return user_dict

  def to_json(self):
    # build data from entries
    data = {}
    entries = self.entries
    for e in entries:
      e_dict = e.to_dict()
      data[e_dict['date']] = e_dict
    
    # add data to user dict
    u_dict = self.to_dict()
    u_dict['data'] = data

    return json.dumps(u_dict)

class Entry(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
  date = db.Column(db.DateTime)
  mood = db.Column(db.Integer)
  note = db.Column(db.String)
  
  def __init__(self, mood, note, date = datetime.now()):
    self.mood = mood
    self.note = note
    self.date = date

  def to_dict(self):
    entry_dict = dict(self.__dict__)
    try:
      entry_dict['date'] = format_datetime(entry_dict['date'], 'YYYY-MM-DD')
    except Exception:
      pass
    try:
      del entry_dict['_sa_instance_state']
    except Exception:
      pass
    return entry_dict

  def to_json(self):
    return json.dumps(self.to_dict())

# Scripts
@manager.command
def migrate_data_to_entries():
    users = User.query.all()
    for u in users:
      datum = u.get_data_as_json()
      for d_key in datum.keys():
        date = datetime.strptime(d_key, "%Y-%m-%d")
        mood = int(datum[d_key]['mood'])
        note = datum[d_key]['note']
        u.entries.append(Entry(mood = mood, note = note, date = date))
      db.session.add(u)
    db.session.commit()

# Utils
def get_or_create_user(phone_number, username = None):
  u = User.query.filter_by(phone_number = phone_number).first()
  if u:
    return u
  else:
    u = User(phone_number = phone_number, username = username)
    db.session.add(u)
    send_message(u.phone_number, render_template('welcome.html', user = u))
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

if __name__ == '__main__':
    manager.run()