import os, urllib2
import json
import re
import operator
from twilio.rest import TwilioRestClient
from datetime import datetime, timedelta, date
from babel.dates import format_datetime
from flask import Flask, request, render_template, redirect, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

# Setup app
app = Flask(__name__)
app.config['DEBUG'] = os.environ['DEBUG']
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

# Setup scripts
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
  return u.to_json() if u.to_json() else 'no data here...'

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')
  u = get_or_create_user(from_number, msg)
  app.logger.info('SMS From: %s, Msg: %s, User: %s' %(from_number, msg, u.username))

  # Check for invite
  invited_phone_number = parse_phone_number(msg)
  if u and invited_phone_number:
    app.logger.info('Inviting phone #: %s' % invited_phone_number)
    invited_u = User.query.filter_by(phone_number = invited_phone_number).first()
    if invited_u:
      app.logger.info('Invited duplicate...')
      send_message(invited_u.phone_number, render_template('poke.html'))
      return send_message(from_number, render_template('duplicate-invite.html'))
    else:
      app.logger.info('Successfully invited %s!' % invited_phone_number)
      send_message(from_number, render_template('thanks-invite.html'))
      return send_message(invited_phone_number, render_template('invite.html'))

  # Add entry
  # Change this to parse_entry and get m and note from it
  elif u and valid_entry(msg):
    entry = Entry(msg[0], msg)
    u.entries.append(entry)
    db.session.add(u)
    db.session.commit()
    return 'added entry: %s' % msg
  else:
    return "invalid msg..."

# Models
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username_url = db.Column(db.String(80), unique=True)
  username = db.Column(db.String(80))
  phone_number = db.Column(db.String(20), unique=True)
  entries = db.relationship('Entry', backref='user', lazy='dynamic')
  data = db.Column(db.Text())
  
  def __init__(self, phone_number, username):
    username_url = username_to_url(username)
    self.phone_number = phone_number
    self.username = username
    self.username_url = username_url

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

    # save before noon as 11pm yesterday
    hr = int(format_datetime(date, 'HH'))
    if hr < 12:
      self.date = date - timedelta(hours = hr + 1)
    else:
      self.date = date

  def to_dict(self):
    entry_dict = dict(self.__dict__)
    try:
      entry_dict['date'] = format_datetime(entry_dict['date'], 'YYYY-MM-dd')
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

@manager.command
def send_nightly_reminder():
  users = User.query.all()
  send_announcement(render_template('nightly-reminder.html'), users)

@manager.command
def test_nightly_reminder():
  users = [User.query.filter_by(username = 'Jake').first()]
  send_announcement(render_template('nightly-reminder.html'), users)

@manager.command
def send_morning_reminder():
  yesterday = date.today() - timedelta(days = 1)
  users_to_remind = get_pending_users(day = yesterday)
  send_announcement(render_template('morning-reminder.html'), users_to_remind)

# Utils
def username_to_url(username):
    url = re.sub('[!@#$]', '', username)
    url = url.strip()
    url = url.replace(" ","-")
    url = url.lower()
    return url

def get_pending_users(day = date.today()):
  '''Get users who haven't logged the given day'''
  # set to midnight
  day = datetime.combine(day, datetime.min.time())
  pending_users = []
  users = User.query.all()
  for u in users:
    # This is a bug...will only work for yesterday right now
    if u.entries.filter(Entry.date >= day).first() is None:
      pending_users.append(u)
  return pending_users

def get_or_create_user(phone_number, username = None):
  # Get existing users
  u = User.query.filter_by(phone_number = phone_number).first()
  if u:
    app.logger.info('Found existing user: %s' % u.username)
    return u
  
  # Check for duplicate username
  elif User.query.filter_by(username_url = username_to_url(username)).first():
    app.logger.info('Duplicate username')
    send_message(phone_number, render_template('username-taken.html', username = username))
    raise ValueError('Username taken. Try again!')

  # Create new user
  else:
    app.logger.info('Creating new user: %s' % username)
    u = User(phone_number = phone_number, username = username)
    db.session.add(u)
    send_message(u.phone_number, render_template('welcome.html', user = u))
    return u

def send_announcement(body, users = None):
  for u in users:
    send_message(u.phone_number, body)

def send_message(phone_number, body):
  account_sid = os.environ['TWILIO_SID']
  auth_token = os.environ['TWILIO_AUTH']
  twilio_number = os.environ['TWILIO_NUM']
  client = TwilioRestClient(account_sid, auth_token)
  client.sms.messages.create(to=phone_number, from_=twilio_number, body=body[:160])
  return body

def valid_entry(msg):
  if msg and msg[0].isdigit() and int(msg[0]) in range(1,6):
    return True
  else:
    return False

def parse_phone_number(msg):
  phone_re = re.compile(r'\(?(\d{3})\)?[ -.]?(\d{3})[ -.]?(\d{4})', re.VERBOSE)
  m = phone_re.search(msg)
  if m:
    phone_number = '+1' + m.group(1) + m.group(2) + m.group(3)
    return phone_number

if __name__ == '__main__':
    manager.run()