# coding: utf-8
import unittest
from time import sleep
from flask import url_for
from sayit.models import Reply, Topic
from sayit.exts import db
from base_setup import BaseSetup


class ApiTestCase(BaseSetup):
    def test_upvote_topic(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'title="赞"', self.as_text(resp))
            self.log_out()

        self.login_user(username=u2.username)
        self.post_to(url_for('api.upvote'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'title="取消赞"', self.as_text(resp))
        self.log_out()

        self.login_user(username=u1.username)
        self.post_to(url_for('api.upvote'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'2 个赞', self.as_text(resp))
        self.log_out()

        # cancel
        self.login_user(username=u2.username)
        self.post_to(url_for('api.upvote'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'1 个赞', self.as_text(resp))

    def test_upvote_reply(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            self.commit_reply(1, u'抢沙发🐶🐱')
            self.log_out()

        self.login_user(username=u2.username)
        self.post_to(url_for('api.upvote'), dict(type='reply', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'title="取消赞"', self.as_text(resp))
        self.log_out()

        self.login_user(username=u1.username)
        self.post_to(url_for('api.upvote'), dict(type='reply', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'>2 个赞<', self.as_text(resp))
        self.log_out()

        # cancel
        self.login_user(username=u2.username)
        self.post_to(url_for('api.upvote'), dict(type='reply', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'>1 个赞<', self.as_text(resp))

    def test_follow_topic(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            self.log_out()

        self.login_user(username=u2.username)
        self.client.post(url_for('api.follow'), data=dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'title="取消关注"', self.as_text(resp))
        self.log_out()

        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'>1 个关注<', self.as_text(resp))

        # cancel
        self.login_user(username=u2.username)
        self.post_to(url_for('api.follow'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        # print self.as_text(resp).encode('utf-8')
        self.assertIn(u'>关注<', self.as_text(resp))

    def test_bookmark_topic(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'title="收藏"', self.as_text(resp))
            self.log_out()

        self.login_user(username=u2.username)
        self.post_to(url_for('api.bookmark'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'title="取消收藏"', self.as_text(resp))
        self.log_out()

        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'1 个收藏', self.as_text(resp))

        # cancel
        self.login_user(username=u2.username)
        self.post_to(url_for('api.bookmark'), dict(type='topic', id=1))
        resp = self.client.get(url_for('topic.single_topic', topic_id=1))
        self.assertIn(u'>收藏<', self.as_text(resp))

    def test_follow_user(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        resp = self.client.get(url_for('user.view_user', username=u1.username))
        self.assertIn(u'follower">0</a>', self.as_text(resp))
        # u2 follow u1
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            self.post_to(url_for('api.follow'), dict(type='user', id=1))
        # check act on user page u1
        resp = self.client.get(url_for('user.view_user',
                                       username=u1.username,
                                       tab='follower'))
        self.assertIn(u'>取消关注<', self.as_text(resp))
        self.assertIn(u'follower">1</a>', self.as_text(resp))
        self.assertIn(u2.username, self.as_text(resp))
        self.log_out()
        # u1 should list in u2 following
        resp = self.client.get(url_for('user.view_user',
                                       username=u2.username,
                                       tab='following'))
        self.assertIn(u1.username, self.as_text(resp))

        # cancel
        self.login_user(username=u2.username)
        self.post_to(url_for('api.follow'), dict(type='user', id=1))
        resp = self.client.get(url_for('user.view_user',
                                       username=u1.username,
                                       tab='follower'))
        self.assertIn(u'follower">0</a>', self.as_text(resp))

    def test_block_user(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        # u2 on u1
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            resp = self.client.get(url_for('user.view_user', username=u1.username))
            # not block yet
            self.assertIn(u'>屏蔽<', self.as_text(resp))
            self.post_to(url_for('api.block'), dict(type='user', id=1))
            # block working
            resp = self.client.get(url_for('user.view_user', username=u1.username))
            self.assertIn(u'>取消屏蔽<', self.as_text(resp))
            # cancel
            self.post_to(url_for('api.block'), dict(type='user', id=1))
            resp = self.client.get(url_for('user.view_user', username=u1.username))
            # not block yet
            self.assertIn(u'>屏蔽<', self.as_text(resp))

    def test_user_json_list(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            resp = self.client.get(url_for('api.user_json'))
            self.assertIn(u1.username, self.as_text(resp))
            self.assertIn(u2.username, self.as_text(resp))

    def test_elite_pin(self):
        u1 = self.commit_user(name='user1')
        u1.set_admin_role()
        db.session.commit()
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            self.commit_topic(title='titletexthere', login=False)
            self.log_out()

            self.login_user(username=u1.username)
            self.post_to(url_for('api.elite_pin'), dict(action='elite', tid=1))
            self.post_to(url_for('api.elite_pin'), dict(action='pin', tid=1))
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'精华帖！', self.as_text(resp))
            self.assertIn(u'fa-thumb-tack', self.as_text(resp))
            # cancel
            self.post_to(url_for('api.elite_pin'), dict(action='elite', tid=1))
            self.post_to(url_for('api.elite_pin'), dict(action='pin', tid=1))
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertNotIn(u'精华帖！', self.as_text(resp))
            self.assertNotIn(u'fa-thumb-tack', self.as_text(resp))

    def test_delete_reply(self):
        u1 = self.commit_user(name='admin')
        u1.set_admin_role()
        db.session.commit()
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            self.commit_topic(title='titletexthere', login=False)
            self.commit_reply(1, u'抢沙发🐶🐱')
            self.log_out()

            self.login_user(username=u1.username)
            self.post_to(url_for('api.delete_post'), dict(type='reply', id=1))
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'>已被 admin 删除<', self.as_text(resp))
            self.log_out()

            # non admin user just show reply is delete
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'1 楼已删除', self.as_text(resp))

    def test_delete_topic(self):
        u1 = self.commit_user(name='admin')
        u1.set_admin_role()
        db.session.commit()
        u2 = self.commit_user(name='user2')
        with self.app.test_request_context():
            self.login_user(username=u2.username)
            self.commit_topic(title='titletexthere', login=False)
            self.log_out()

            self.login_user(username=u1.username)
            self.post_to(url_for('api.delete_post'), dict(type='topic', id=1))
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertIn(u'>已被 admin 删除<', self.as_text(resp))
            self.log_out()

            # non admin user return 404
            resp = self.client.get(url_for('topic.single_topic', topic_id=1))
            self.assertTrue(resp.status_code == 404)

    def test_edit_email(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        u1.email_confirmed = 0
        u2.email_confirmed = 0
        db.session.commit()
        with self.app.test_request_context():
            self.login_user(username=u1.username)
            # exist address of u2
            resp = self.client.post(url_for('api.edit_email'),
                                    data=dict(address=u2.email))
            self.assertIn('exist', self.as_text(resp))
            # spam check
            for _ in range(4):
                resp = self.client.post(url_for('api.edit_email'),
                                        data=dict(address='new@test.com'),
                                        follow_redirects=True)
            self.assertIn('limit', self.as_text(resp))
            self.log_out()
            # success send
            self.login_user(username=u2.username)
            resp = self.client.post(url_for('api.edit_email'),
                                    data=dict(address='new@test.com'))
            self.assertIn('send', self.as_text(resp))


if __name__ == '__main__':
    unittest.main()
