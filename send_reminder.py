from moodsms import *

users = User.query.all()
reminder_message = '''How was your day? Reply with a number 1-5 and a note, like this:
'5. Awesome day hiking!'
'1. Terrible day :(!
Good night :)'''

for u in users:
  try:
    send_message(u.phone_number, reminder_message)
  except Exception:
    pass