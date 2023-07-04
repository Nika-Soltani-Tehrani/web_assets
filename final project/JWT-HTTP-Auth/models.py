from sqlalchemy.sql import func
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship
from init import app
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

database = SQLAlchemy(app)
marshmallow = Marshmallow(app)


class Users(database.Model):
    id = database.Column('id', database.Integer, primary_key=True)
    created_at = database.Column(DateTime(), server_default=func.now())
    updated_at = database.Column(DateTime(), onupdate=func.now())
    username = database.Column(database.String(255))
    password = database.Column(database.String(255))

    urls_relation = relationship("URLs", back_populates="user_relation")


class URLs(database.Model):
    id = database.Column('id', database.Integer, primary_key=True)
    created_at = database.Column(DateTime(), server_default=func.now())
    updated_at = database.Column(DateTime(), onupdate=func.now())
    user_id = database.Column(database.Integer, ForeignKey(Users.id))
    address = database.Column(database.String(255))
    threshold = database.Column(database.Integer)

    user_relation = relationship("Users", back_populates="urls_relation")
    requests_relation = relationship("Requests", back_populates="url_relation")


class Requests(database.Model):
    id = database.Column('id', database.Integer, primary_key=True)
    created_at = database.Column(DateTime(), server_default=func.now())
    updated_at = database.Column(DateTime(), onupdate=func.now())
    url_id = database.Column(database.Integer, ForeignKey(URLs.id))
    result = database.Column(database.Integer)

    url_relation = relationship("URLs", back_populates="requests_relation")


class UsersSchema(marshmallow.SQLAlchemyAutoSchema):
    class Meta:
        model = Users


class URLsSchema(marshmallow.SQLAlchemyAutoSchema):
    class Meta:
        model = URLs


class RequestsSchema(marshmallow.SQLAlchemyAutoSchema):
    class Meta:
        model = Requests

    url = marshmallow.Nested(URLsSchema)


if __name__ == "__main__":
    with app.app_context():
        database.create_all()
