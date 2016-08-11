import inspect
from flask import Flask
from werkzeug.utils import import_string
from flask_sqlalchemy import models_committed
from config import config
from exts import bcrypt, db, csrf, mail, celery, login_manager, redis_store
from db_monitor import receive_change

blueprints = [
        ('home:home', '/'),
        ('user:user', '/user'),
        ('account:account', '/account'),
        ('topic:topic', '/topic'),
        ('notice:notice', '/notifications'),
        ('api:api', '/api'),
            ]

jinja_filters = [
    ('add_delimiter', 'addlt'),
    ('get_reply_upvote_count', 'rupvo'),
    ('user_unread_notice_count', 'ucount'),
    ('topic_cached_count', 'cachecount'),
    ('topic_last_reply', 'lastreply'),
    ('node_name', 'nname'),
    ('chs_time', 'chstime'),
    ('check_can_post', 'canpost'),
        ]


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    csrf.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    redis_store.init_app(app)
    celery.conf.update(app.config)

    models_committed.connect(receive_change, app)

    sign_in_manage = {}
    sign_in_func = 'account.sign_in'
    for path in blueprints:
        bp = import_string('sayit.views.' + path[0])
        app.register_blueprint(bp, url_prefix=path[1])
        sign_in_manage[bp.name] = sign_in_func

    for path in jinja_filters:
        flt = import_string('sayit.filters:' + path[0])
        app.jinja_env.filters[path[1]] = flt

    login_manager.blueprint_login_views = sign_in_manage

    return app


def get_models():
    import models
    all_models = {}
    for name, obj in inspect.getmembers(models, inspect.isclass):
        if issubclass(obj, db.Model) and name != db.Model.__name__:
            all_models[name] = obj
    return all_models
