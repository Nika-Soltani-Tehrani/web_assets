
from sqlalchemy.sql import func
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from init import app

db = SQLAlchemy(app)
ma= Marshmallow(app)

#----------------------------------------------------------------------------#
# Models
#----------------------------------------------------------------------------#

class Users(db.Model):
   id = db.Column('id', db.Integer, primary_key = True)
   username = db.Column(db.String(255))
   password = db.Column(db.String(255))
   created_at = db.Column(DateTime(timezone=True), server_default=func.now()) 
   updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

   urls = relationship("URLs", back_populates="user")

class URLs(db.Model):
   id = db.Column('id', db.Integer, primary_key = True)
   user_id = db.Column(db.Integer, ForeignKey(Users.id))
   address = db.Column(db.String(255))
   threshold = db.Column(db.Integer)
   created_at = db.Column(DateTime(timezone=True), server_default=func.now()) 
   updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

   user = relationship("Users", back_populates="urls")
   requests = relationship("Requests", back_populates="url")

class Requests(db.Model):
   id = db.Column('id', db.Integer, primary_key = True)
   url_id = db.Column(db.Integer, ForeignKey(URLs.id))
   result = db.Column(db.Integer)
   created_at = db.Column(DateTime(timezone=True), server_default=func.now()) 
   updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

   url = relationship("URLs", back_populates="requests")

#----------------------------------------------------------------------------#
# Serializers
#----------------------------------------------------------------------------#

class UsersSchema(ma.SQLAlchemyAutoSchema):
   class Meta:
      model = Users

class URLsSchema(ma.SQLAlchemyAutoSchema):
   class Meta:
      model = URLs

class RequestsSchema(ma.SQLAlchemyAutoSchema):
   class Meta:
      model = Requests

   url = ma.Nested(URLsSchema)