# coding: utf-8
import os
from flask_bcrypt import Bcrypt
from celery import Celery
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, AnonymousUserMixin
from flask_wtf.csrf import CsrfProtect
from flask_redis import FlaskRedis
from redis import StrictRedis
from qiniu import Auth
from . import config


class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.is_admin = False


def get_app_config():
    return config[os.getenv('FLKCONF') or 'product']

login_manager = LoginManager()
login_manager.login_message = u'请登录后浏览'
login_manager.login_message_category = 'warning'
login_manager.anonymous_user = Anonymous

db = SQLAlchemy()

bcrypt = Bcrypt()

mail = Mail()

celery = Celery(__name__, broker=get_app_config().CELERY_BROKER_URL)

csrf = CsrfProtect()

redis_store = FlaskRedis.from_custom_provider(StrictRedis)

qniu = Auth(get_app_config().QINIU_ACCESS_KEY, get_app_config().QINIU_SECRET_KEY)
