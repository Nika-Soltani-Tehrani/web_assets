from flask import request, Response, json
from functools import wraps
from models import Users
import jwt


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
