from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

app = Flask('JWT-HTTP-Auth')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.secret_key = 'test'
sleeping_time = 5
database = SQLAlchemy(app)
marshmallow = Marshmallow(app)

import views
