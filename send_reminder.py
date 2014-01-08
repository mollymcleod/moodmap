from moodsms import *

users = User.query.all()
reminder_message = 'How was your day? Reply 1-5 and a note.'
for u in users:
  try:
    send_message(u.phone_number, reminder_message)
  except Exception:
    pass