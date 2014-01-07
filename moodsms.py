import os, urllib2
import json
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
  u = User.query.filter_by(phone_number = phone_number).first()
  return render_template('calendar.html', data = u.data)

@app.route('/sms')
def sms():
  msg = request.values.get('Body')
  from_number = request.values.get('From')
  u = get_or_create_user(from_number)

  # add element
  datum = {'date' : format_datetime(datetime.now(), 'YYYY-MM-DD'),
          'mood': msg[0],
          'note' : msg}
  u.add_datum(datum)
  db.session.add(u)
  return "added row"

# Models
class User(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  phone_number = db.Column(db.String(11), unique=True)
  data = db.Column(db.Text())
  
  def __init__(self, phone_number, data = None):
    self.phone_number = phone_number
    self.data = data

  def save_json_as_text(self, json_data):
    text_data = json.dumps(json_data)
    self.data = text_data

  def get_data_as_json(self):
    return json.loads(self.data)

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
    return User(phone_number = phone_number)

def add_row(row):
  if len(row) == 3:
    next_row = len(wks.col_values(1)) + 1
    for index, c in enumerate(row):
      wks.update_cell(next_row, index+1, c)