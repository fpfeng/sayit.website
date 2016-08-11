# coding: utf-8
import unittest
from time import sleep
from signal import SIGINT, SIGTERM
from os import environ, devnull, killpg, setsid
from subprocess import Popen, PIPE, STDOUT
from flask import url_for
from sayit import create_app
from sayit.exts import db
from sayit.exts import redis_store
from sayit.models import User, UserRole, Node


class BaseSetup(unittest.TestCase):
    def setUp(self):
        self.celery_proc = Popen(
            '''export FLKCONF="test" && exec celery -A \
            sayit.celery_worker.celery worker -l info -n test --purge''',
            env=environ.copy(), shell=True, stdout=PIPE, stderr=STDOUT,
            preexec_fn=setsid)
        self.app = create_app('test')
        self.app_ctx = self.app.app_context()
        self.app_ctx.push()
        db.create_all()
        self.client = self.app.test_client(use_cookies=True)
        self.email = 'test@example.com'
        self.password = 'testpassword'
        self.username = 'testuser'
        UserRole.create_role()
        Node.create_node()

    def tearDown(self):
        db.session.rollback()
        db.session.remove()
        db.drop_all()
        # start outside first
        # celery multi start 1 -A sayit.celery_worker.celery worker -l debug
        # --pidfile=/tmp/celery_test_sayit/%n.pid
        # --logfile=/tmp/celery_test_sayit/%N.log
        # this is stupid or wrong
        # redis_store.flushdb()
        # self.celery_proc.terminate()
        killpg(self.celery_proc.pid, SIGTERM)
        self.celery_proc.wait()
        # for _ in range(3):
        #     self.celery_proc.send_signal(SIGINT)
        # subprocess.check_output(
        #     "ps auxww | grep 'celery worker'",
        #     env=os.environ.copy(), shell=True)
        self.app_ctx.pop()
        redis_store.flushdb()  # cleanup cache database, not celery broker

    def add_user_row(self, name='testuser'):
        return User(username=name,
                    role_id=4,
                    password='testpassword',
                    email='test@example.com')

    def commit_user(self, name='userone', role=3):
        u = User(username=name,
                 role_id=role,
                 password='testpassword',
                 email='{0}@example.com'.format(name),
                 email_confirmed=1)
        db.session.add(u)
        db.session.commit()
        return u

    def topic_body(self, title=u'🐷🐶🐱标题😠title😊123😊'):
        t = {
            'node': 101,
            'title': title,
            'content': u'🐷🐶🐱内容content2😠测试test😊456😊'
        }
        return t

    def add_user(self):
        user = self.add_user_row()
        db.session.add(user)
        db.session.commit()
        return user

    def commit_topic(self, title=u'内容content2🐷🐶🐱测试', login=True):
        if login:
            self.login_user()
        attr = self.topic_body(title)
        self.client.post(url_for('topic.new_topic'),
                         data=attr,
                         follow_redirects=True)

    def log_out(self):
        self.client.get(url_for('account.sign_out'))

    def login_user(self, username=None, password=None):
        if not username:
            username = self.username
        if not password:
            password = self.password
        self.client.post(url_for('account.sign_in'), data=dict(
                username=username,
                password=password,
                ), follow_redirects=True)

    def commit_reply(self, tid, content=u'🐷🐶🐱内容content2😠测试test😊456😊'):
        self.client.post(url_for('topic.add_reply', topic_id=tid),
                         data=dict(
                                content=content
                                ),
                         follow_redirects=True)

    def as_text(self, resp):
        return resp.get_data(as_text=True)

    def post_to(self, url, data):
        self.client.post(url, data=data)
