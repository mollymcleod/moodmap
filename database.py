from moodsms import *

def recreate():
  db.drop_all()
  db.create_all()

def seed():
  u = User(phone_number = '+15102068727')
  data = {"2014-01-01"  : {'mood' : '3', 'note' : 'Rose bowl. Tired and antisocial. Bball after. Okay...'},
          "2014-01-02"  : {'mood' : '3', 'note' : 'Strong day. Moms bday. Now bloodhound w roomies.'},
          "2014-01-03"  : {'mood' : '3', 'note' : 'Solid day. Hank. Marc lunch. David to chat about work. Bball. Home reading.'},
          "2014-01-04"  : {'mood' : '3', 'note' : 'Writing in morning at farleys. Football and beer. Nap. Relax...not going out tnight.'},
          "2014-01-05"  : {'mood' : '4', 'note' : 'Put out people not data post. Great reception. Bad first date at Jupiter. Home.'}}
  u.data = json.dumps(data)
  db.session.add(u)
  db.session.commit()

def reset_db():
  recreate()
  seed()