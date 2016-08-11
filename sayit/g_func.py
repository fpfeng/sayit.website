from flask import g
from flask_login import current_user
from . import db


def user_and_session():
    g.user = current_user
    g.session = db.session
