from functools import wraps
import jwt
from flask import request, jsonify, Response, json

from init import app
from init import database
from models import Users, URLs, Requests, URLsSchema, RequestsSchema

import datetime


def count_success_requests(requests_list):
    count = 0
    for request in requests_list:
        if 200 <= request['result'] <= 299:
            count += 1
    return count


def count_failure_requests(requests_list):
    count = 0
    for request in requests_list:
        if request['result'] < 200 or request['result'] > 299:
            count += 1
    return count


def jwt_auth(f):
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


@app.route('/', methods=['GET'])
def test():
    return 'hello'


@app.route('/api/login', methods=['POST'])
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
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
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


@app.route('/api/add_user', methods=['POST'])
def add_user():
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
            user = Users(username=request.form['username'], password=request.form['password'], )
            database.session.add(user)
            database.session.commit()
            return Response(
                response=json.dumps({
                    "message": "user signed up successfully"
                }),
                status=200,
                mimetype="application/json"
            )


@app.route('/api/add_url', methods=['POST'])
@jwt_auth
def add_url(requested_user):
    if not request.form['address'] or not request.form['threshold']:
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

        url_schema = URLsSchema()
        urls = [url_schema.dump(url) for url in URLs.query.filter_by(user_id=requested_user.id)]
        if len(urls) >= 20:
            return Response(
                response=json.dumps({
                    "message": "exceeding maximum number of urls for user"
                }),
                status=409,
                mimetype="application/json"
            )

        else:
            url = URLs(address=request.form['address'], threshold=request.form['threshold'], user_id=requested_user.id)
            database.session.add(url)
            database.session.commit()
            return Response(
                response=json.dumps({
                    "message": "url added to database for this user"
                }),
                status=200,
                mimetype="application/json"
            )


@app.route('/api/get_urls', methods=['GET'])
@jwt_auth
def get_urls(requested_user):
    url_schema = URLsSchema()
    return jsonify(urls=[url_schema.dump(url) for url in URLs.query.filter_by(user_id=requested_user.id)])


@app.route('/api/get_requests', methods=['GET'])
@jwt_auth
def get_requests(requested_user):
    if not request.args.get('url') or not request.args.get('from_date') or not request.args.get('to_date'):
        return Response(
            response=json.dumps({
                "message": "missing query parameter"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        requests_schema = RequestsSchema()
        user_requests = Requests.query.join(URLs).filter(URLs.user_id == requested_user.id)
        url_obj = URLs.query.filter_by(address=request.args.get('url'), user_id=requested_user.id)
        if not url_obj.all():
            return Response(
                response=json.dumps({
                    "message": "no request is available"
                }),
                status=404,
                mimetype="application/json"
            )

        requests = [requests_schema.dump(request) for request in
                    user_requests.filter(Requests.url_id == url_obj.all()[0].id,  # filtering url_id
                                         Requests.created_at >= datetime.datetime.strptime(request.args\
                                                                                           .get('from_date'),\
                                                                                           "%Y-%m-%d"),
                                         Requests.created_at <= datetime.datetime.strptime(
                                             request.args.get('to_date'), "%Y-%m-%d")
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
            num_of_requests = len(requests)
            num_of_success = count_success_requests(requests)
            num_of_failure = count_failure_requests(requests)
            return jsonify(num_of_requests=num_of_requests,
                           num_of_success=num_of_success,
                           num_of_failure=num_of_failure,
                           requests=requests
                           )


@app.route('/api/add_request', methods=['POST'])
@jwt_auth
def add_request(requested_user):
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
        database.session.add(request_data)
        database.session.commit()
        return Response(
            response=json.dumps({
                "message": "request added to database for this url id"
            }),
            status=200,
            mimetype="application/json"
        )


@app.route('/api/get_alerts', methods=['GET'])
@jwt_auth
def get_alerts(input_user):
    if not request.args.get('url') or not request.args.get('from_date') or not request.args.get('to_date'):
        return Response(
            response=json.dumps({
                "message": "missing query parameter"
            }),
            status=422,
            mimetype="application/json"
        )
    else:
        requests_schema = RequestsSchema()
        user_requests = Requests.query.join(URLs).filter(URLs.user_id == input_user.id)

        url_obj = URLs.query.filter_by(address=request.args.get('url'), user_id=input_user.id)
        if not url_obj.all():
            return Response(
                response=json.dumps({
                    "message": "no alert is available"
                }),
                status=404,
                mimetype="application/json"
            )

        requests = [requests_schema.dump(request) for request in
                    user_requests.filter(Requests.url_id == url_obj.all()[0].id,
                                         Requests.created_at >= datetime.datetime.strptime(request.args
                                                                                           .get('from_date'),
                                                                                           "%Y-%m-%d"),
                                         Requests.created_at <= datetime.datetime.strptime(
                                             request.args.get('to_date'), "%Y-%m-%d"),
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
            num_of_requests = len(requests)
            num_of_success = count_success_requests(requests)
            num_of_failure = count_failure_requests(requests)
            threshold = url_obj.all()[0].threshold
            if num_of_failure < threshold:
                return Response(
                    response=json.dumps({
                        "message": "no alert is available"
                    }),
                    status=404,
                    mimetype="application/json"
                )
            else:
                return jsonify(message="you have an alert",
                               num_of_requests=num_of_requests,
                               num_of_success=num_of_success,
                               num_of_failure=num_of_failure,
                               requests=requests
                               )
