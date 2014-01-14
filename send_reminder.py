from moodsms import *

users = User.query.all()
reminder_message = '''How was your day? Reply with # + a note about something memorable.
1 = Terrible
5 = Awesome
Good night :)'''

for u in users:
  try:
    send_message(u.phone_number, reminder_message)
  except Exception:
    pass