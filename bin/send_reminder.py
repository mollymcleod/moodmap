import sys, os
from twilio.rest import TwilioRestClient

def send_message(phone_number, body):
  account_sid = os.environ['TWILIO_SID']
  auth_token = os.environ['TWILIO_AUTH']
  twilio_number = os.environ['TWILIO_NUM']
  client = TwilioRestClient(account_sid, auth_token)
  client.sms.messages.create(to=phone_number, from_=twilio_number, body=body[:160])

phone_number = sys.argv[1]
body = 'How was your day? Reply 1-5 and a note'
send_message(phone_number, body)