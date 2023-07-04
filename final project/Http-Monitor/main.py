# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

from flask import Flask, request, flash, jsonify, Response, json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship
from flask_marshmallow import Marshmallow
import jwt
from functools import wraps
from datetime import datetime, timedelta
from utils import toDateTime, countRequests, countSuccessRequests, countFailiureRequests

# ----------------------------------------------------------------------------#
# Config Flask App
# ----------------------------------------------------------------------------#

app = Flask('http-monitor')
app.secret_key = 'bccaa336-98c6-11ed-a8fc-0242ac120002'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'

db = SQLAlchemy(app)
ma = Marshmallow(app)

# ----------------------------------------------------------------------------#
# ENV Variables
# ----------------------------------------------------------------------------#

MAX_URLS_FOR_USER = 3


# ----------------------------------------------------------------------------#
# Models
# ----------------------------------------------------------------------------#

class Users(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    username = db.Column(db.String(255))
    password = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean)
    created_at = db.Column(DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

    urls = relationship("URLs", back_populates="user")


class URLs(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey(Users.id))
    address = db.Column(db.String(255))
    threshold = db.Column(db.Integer)
    checking_seconds = db.Column(db.Integer)
    last_checking_date = db.Column(DateTime(timezone=True), server_default=func.now())
    created_at = db.Column(DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("Users", back_populates="urls")
    requests = relationship("Requests", back_populates="url")


class Requests(db.Model):
    id = db.Column('id', db.Integer, primary_key=True)
    url_id = db.Column(db.Integer, ForeignKey(URLs.id))
    result = db.Column(db.Integer)
    created_at = db.Column(DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(DateTime(timezone=True), onupdate=func.now())

    url = relationship("URLs", back_populates="requests")


# ----------------------------------------------------------------------------#
# Serializers
# ----------------------------------------------------------------------------#

class UsersSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Users


class URLsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = URLs

    # user_id = ma.auto_field(dump_only=True) --> used if we want to take only one column from related table
    user = ma.Nested(UsersSchema)


class RequestsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Requests

    url = ma.Nested(URLsSchema)


# ----------------------------------------------------------------------------#
# JWT Decorator
# ----------------------------------------------------------------------------#

def token_check(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        if not token:
            return Response(
                response=json.dumps({
                    "message": "token not available"
                }),
                status=401,
                mimetype="application/json"
            )

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'])
            requested_user = Users.query.filter_by(id=data['id']).first()
        except:
            return Response(
                response=json.dumps({
                    "message": "incorrect token"
                }),
                status=401,
                mimetype="application/json"
            )

        return f(requested_user, *args, **kwargs)

    return decorated


# ----------------------------------------------------------------------------#
# Endpoints For Users
# ----------------------------------------------------------------------------#

@app.route('/v1/users/login', methods=['POST'])
def login():
    if not request.form['username'] or not request.form['password']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        user = Users.query.filter_by(username=request.form['username']).first()
        if not user:
            return Response(
                response=json.dumps({
                    "message": "user not available"
                }),
                status=404,
                mimetype="application/json"
            )

        if user.password == request.form['password']:
            token = jwt.encode({
                'id': user.id,
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }, app.config['SECRET_KEY'])

            return Response(
                response=json.dumps({
                    "message": "logged in successfully",
                    "token": token.decode('UTF-8')
                }),
                status=201,
                mimetype="application/json"
            )
        else:
            return Response(
                response=json.dumps({
                    "message": "wrong password",
                }),
                status=403,
                mimetype="application/json"
            )


@app.route('/v1/users/signup', methods=['POST'])
def signup():
    if not request.form['username'] or not request.form['password']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        user = Users.query.filter_by(username=request.form['username']).first()
        if user:
            return Response(
                response=json.dumps({
                    "message": "user already exists"
                }),
                status=409,
                mimetype="application/json"
            )
        else:
            user = Users(username=request.form['username'], password=request.form['password'], is_admin=False)
            db.session.add(user)
            db.session.commit()
            return Response(
                response=json.dumps({
                    "message": "user signed up successfully"
                }),
                status=200,
                mimetype="application/json"
            )


@app.route('/v1/users/all', methods=['GET'])
@token_check
def get_all_users(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )
    user_schema = UsersSchema()
    return jsonify(users=[user_schema.dump(user) for user in Users.query.all()])


# ----------------------------------------------------------------------------#
# Endpoints For URLs
# ----------------------------------------------------------------------------#

@app.route('/v1/urls/all', methods=['GET'])
@token_check
def get_all_urls(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )
    url_schema = URLsSchema()
    return jsonify(urls=[url_schema.dump(url) for url in URLs.query.all()])


@app.route('/v1/urls/add', methods=['POST'])
@token_check
def add_url(requested_user):
    if not request.form['address'] or not request.form['threshold'] or not request.form['checking_seconds']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        url = URLs.query.filter_by(address=request.form['address'], user_id=requested_user.id).first()
        if url:
            return Response(
                response=json.dumps({
                    "message": "url already exists for this user"
                }),
                status=409,
                mimetype="application/json"
            )
        ####### limiting number of user url to MAX_URLS_FOR_USER
        url_schema = URLsSchema()
        urls = [url_schema.dump(url) for url in URLs.query.filter_by(user_id=requested_user.id)]
        if len(urls) >= MAX_URLS_FOR_USER:
            return Response(
                response=json.dumps({
                    "message": "exceeding maximum number of urls for user"
                }),
                status=409,
                mimetype="application/json"
            )
        #######
        else:
            url = URLs(address=request.form['address'], threshold=request.form['threshold'],
                       checking_seconds=request.form['checking_seconds'], user_id=requested_user.id)
            db.session.add(url)
            db.session.commit()
            return Response(
                response=json.dumps({
                    "message": "url added to database for this user"
                }),
                status=200,
                mimetype="application/json"
            )


@app.route('/v1/urls/user', methods=['GET'])
@token_check
def get_user_urls(requested_user):
    url_schema = URLsSchema()
    return jsonify(urls=[url_schema.dump(url) for url in URLs.query.filter_by(user_id=requested_user.id)])


@app.route('/v1/urls/checked', methods=['POST'])
@token_check
def update_url_checking_date(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )

    if not request.form['url_id']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        URLs.query.filter_by(id=request.form['url_id']).all()[0].last_checking_date = datetime.now().replace(
            microsecond=0)
        db.session.commit()
        return Response(
            response=json.dumps({
                "message": "last checking date updated to now"
            }),
            status=200,
            mimetype="application/json"
        )


@app.route('/v1/urls/update-checking-seconds', methods=['POST'])
@token_check
def update_url_checking_seconds(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )

    if not request.form['checking_seconds'] or not request.form['url_id']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        URLs.query.filter_by(id=request.form['url_id']).all()[0].checking_seconds = request.form['checking_seconds']
        db.session.commit()
        return Response(
            response=json.dumps({
                "message": "checking seconds updated"
            }),
            status=200,
            mimetype="application/json"
        )


# ----------------------------------------------------------------------------#
# Endpoints For Requests
# ----------------------------------------------------------------------------#

@app.route('/v1/requests/all', methods=['GET'])
@token_check
def get_all_requests(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )
    request_schema = RequestsSchema()
    return jsonify(requests=[request_schema.dump(request) for request in Requests.query.all()])


@app.route('/v1/requests', methods=['GET'])
@token_check
def get_url_requests(requested_user):
    if not request.args.get('url') or not request.args.get('from_date') or not request.args.get('to_date'):
        return Response(
            response=json.dumps({
                "message": "missing query parameter"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        reqeusts_schema = RequestsSchema()
        user_requests = Requests.query.join(URLs).filter(URLs.user_id == requested_user.id)
        # getting the url object that satisfy user id and address (in order to find url_id)
        url_obj = URLs.query.filter_by(address=request.args.get('url'), user_id=requested_user.id)
        if not url_obj.all():
            return Response(
                response=json.dumps({
                    "message": "no request is available"
                }),
                status=404,
                mimetype="application/json"
            )

        requests = [reqeusts_schema.dump(request) for request in
                    user_requests.filter(Requests.url_id == url_obj.all()[0].id,  # filtering url_id
                                         Requests.created_at >= toDateTime(request.args.get('from_date')),
                                         # filtering from_time
                                         Requests.created_at <= toDateTime(request.args.get('to_date'))
                                         # filtering to_time
                                         )]

        if not requests:
            return Response(
                response=json.dumps({
                    "message": "no request is available"
                }),
                status=404,
                mimetype="application/json"
            )
        else:
            numberOfRequests = countRequests(requests)
            numberOfSuccessRequests = countSuccessRequests(requests)
            numberOfFailiureRequests = countFailiureRequests(requests)
            return jsonify(numberOfRequests=numberOfRequests,
                           numberOfSuccessRequests=numberOfSuccessRequests,
                           numberOfFailiureRequests=numberOfFailiureRequests,
                           requests=requests
                           )


@app.route('/v1/requests/add', methods=['POST'])
@token_check
def add_request(requested_user):
    if not requested_user.is_admin:
        return Response(
            response=json.dumps({
                "message": "you are not admin"
            }),
            status=401,
            mimetype="application/json"
        )
    if not request.form['url_id'] or not request.form['result']:
        return Response(
            response=json.dumps({
                "message": "invalid input"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        request_data = Requests(url_id=request.form['url_id'], result=request.form['result'])
        db.session.add(request_data)
        db.session.commit()
        return Response(
            response=json.dumps({
                "message": "request added to database for this url id"
            }),
            status=200,
            mimetype="application/json"
        )


# ----------------------------------------------------------------------------#
# Endpoints For Alerts
# ----------------------------------------------------------------------------#

@app.route('/v1/alerts', methods=['GET'])
@token_check
def get_url_alerts(requested_user):
    print("8888888888888888")
    if not request.args.get('url') or not request.args.get('from_date') or not request.args.get('to_date'):
        return Response(
            response=json.dumps({
                "message": "missing query parameter"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        reqeusts_schema = RequestsSchema()
        user_requests = Requests.query.join(URLs).filter(URLs.user_id == requested_user.id)
        # getting the url object that satisfy user id and address (in order to find url_id)
        url_obj = URLs.query.filter_by(address=request.args.get('url'), user_id=requested_user.id)
        if not url_obj.all():
            return Response(
                response=json.dumps({
                    "message": "no alert is available"
                }),
                status=404,
                mimetype="application/json"
            )

        requests = [reqeusts_schema.dump(request) for request in
                    user_requests.filter(Requests.url_id == url_obj.all()[0].id,  # filtering url_id
                                         Requests.created_at >= toDateTime(request.args.get('from_date')),
                                         # filtering from_time
                                         Requests.created_at <= toDateTime(request.args.get('to_date'))
                                         # filtering to_time
                                         )]

        if not requests:
            return Response(
                response=json.dumps({
                    "message": "no alert is available"
                }),
                status=404,
                mimetype="application/json"
            )
        else:
            numberOfRequests = countRequests(requests)
            numberOfSuccessRequests = countSuccessRequests(requests)
            numberOfFailiureRequests = countFailiureRequests(requests)
            threshold = url_obj.all()[0].threshold
            if numberOfFailiureRequests < threshold:
                return Response(
                    response=json.dumps({
                        "message": "no alert is available"
                    }),
                    status=404,
                    mimetype="application/json"
                )
            else:
                return jsonify(message="you have an alert",
                               numberOfRequests=numberOfRequests,
                               numberOfSuccessRequests=numberOfSuccessRequests,
                               numberOfFailiureRequests=numberOfFailiureRequests,
                               requests=requests
                               )


# ----------------------------------------------------------------------------#
# Launch
# ----------------------------------------------------------------------------#

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
