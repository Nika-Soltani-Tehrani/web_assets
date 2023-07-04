from functools import wraps
import jwt
from datetime import datetime, timedelta
from utils import toDateTime, countRequests, countSuccessRequests, countFailiureRequests
from flask import request, jsonify, Response, json

from init import app
from models import Users, URLs, Requests, UsersSchema, URLsSchema, RequestsSchema

#----------------------------------------------------------------------------#
# JWT Decorator
#----------------------------------------------------------------------------#

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
            requested_user = Users.query.filter_by(id = data['id']).first()
        except:
            return Response(
                        response=json.dumps({
                              "message": "incorrect token"
                        }),
                        status=401,
                        mimetype="application/json"
                     )

        return  f(requested_user, *args, **kwargs)
  
    return decorated


#----------------------------------------------------------------------------#
# Endpoints For Users
#----------------------------------------------------------------------------#

@app.route('/', methods = ['GET'])
def test():
   return 'hello'

@app.route('/v1/users/login', methods =['POST'])
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
      user = Users.query.filter_by(username = request.form['username']).first() 
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
               'exp' : datetime.utcnow() + timedelta(minutes = 30)
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


@app.route('/v1/users/signup', methods = ['POST'])
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
      user = Users.query.filter_by(username = request.form['username']).first()
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


#----------------------------------------------------------------------------#
# Endpoints For URLs
#----------------------------------------------------------------------------#

@app.route('/v1/urls/add', methods = ['POST'])
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
         url = URLs(address=request.form['address'], threshold=request.form['threshold'], checking_seconds=request.form['checking_seconds'], user_id=requested_user.id)
         db.session.add(url)
         db.session.commit()
         return Response(
                           response=json.dumps({
                                 "message": "url added to database for this user"
                           }),
                           status=200,
                           mimetype="application/json"
                        )

@app.route('/v1/urls/user', methods = ['GET'])
@token_check
def get_user_urls(requested_user):
   url_schema = URLsSchema()
   return jsonify(urls = [url_schema.dump(url) for url in URLs.query.filter_by(user_id=requested_user.id)])

#----------------------------------------------------------------------------#
# Endpoints For Requests
#----------------------------------------------------------------------------#

@app.route('/v1/requests', methods = ['GET'])
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
      user_requests = Requests.query.join(URLs).filter(URLs.user_id==requested_user.id)
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
      
      requests = [reqeusts_schema.dump(request) for request in user_requests.filter(Requests.url_id==url_obj.all()[0].id, # filtering url_id
                                                                                               Requests.created_at >= toDateTime(request.args.get('from_date')), # filtering from_time
                                                                                               Requests.created_at <= toDateTime(request.args.get('to_date')) #filtering to_time
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

@app.route('/v1/requests/add', methods = ['POST'])
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

#----------------------------------------------------------------------------#
# Endpoints For Alerts
#----------------------------------------------------------------------------#

@app.route('/v1/alerts', methods = ['GET'])
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
      user_requests = Requests.query.join(URLs).filter(URLs.user_id==requested_user.id)
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
      
      requests = [reqeusts_schema.dump(request) for request in user_requests.filter(Requests.url_id==url_obj.all()[0].id, # filtering url_id
                                                                                               Requests.created_at >= toDateTime(request.args.get('from_date')), # filtering from_time
                                                                                               Requests.created_at <= toDateTime(request.args.get('to_date')) #filtering to_time
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
