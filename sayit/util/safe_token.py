from random import randint
from itsdangerous import URLSafeTimedSerializer
from ..exts import get_app_config


TS = URLSafeTimedSerializer(get_app_config().SECRET_KEY)


def create_email_token(email_address):
    return TS.dumps([email_address, randint(0, 1000)])


def parse_email_address(token):
    return TS.loads(token, max_age=86400)[0]


def create_auth_token(uid_password):
    return TS.dumps(uid_password)


def parse_auth_data(token):
    try:
        return TS.loads(token, max_age=86400 * 90)
    except:
        return None
