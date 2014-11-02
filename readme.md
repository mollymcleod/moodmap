# MoodMap

Simple Flask app that uses Twilio to send people a daily message and turn their responses into a mood map:
![Jake's year](/static/img/jake-calendar.png)

Text a short username to **(510) 213-6505** to get started.

[D3 calendar view from mbostock](http://bl.ocks.org/mbostock/4063318).

## Deploy
You'll need:
- A Twilio account
- PostgresSQL

1) Clone repo:

`git clone https://github.com/lippytak/mood-map.git`

2) Create virtual environment and source it:

`cd mood-map`

`virtualenv venv`

`source venv/bin/activate`

3) Install stuff

`pip install -r requirements.txt`

4) Create a `.env` file with the following variables (remove the brackets):
```
DEBUG=True
TWILIO_NUM=[INSERT TWILIO PHONE NUMBER]
TWILIO_SID=[INSERT TWILIO SID]
TWILIO_AUTH=[INSERT TWILIO AUTH]
DATABASE_URL=postgres://[USERNAME]@localhost/mood
```

5) Setup database

`sudo -u [YOUR POSTGRES USERNAME] createdb mood`

`foreman run python`

`from mood import db`

`db.create_all()`

6) Run locally

`foreman start`

7) Check it out at `localhost:8000`

Remember to source your shell (`source venv/bin/activate`) whenever you restart your terminal.
