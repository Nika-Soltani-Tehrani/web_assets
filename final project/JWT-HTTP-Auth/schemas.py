from init import marshmallow
from models import Users, URLs, Requests


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
