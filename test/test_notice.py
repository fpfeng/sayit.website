# coding: utf-8
import unittest
from time import sleep
from flask import url_for
from sayit.models import Reply, Topic, User, UserNotice
from sayit.exts import db
from base_setup import BaseSetup


class NoticeTestCase(BaseSetup):
    # def setUp(self):
    #     super(NoticeTestCase, self).setUp()
    #     self.req_ctx = self.app.test_request_context()
    #     self.req_ctx.push()

    # def tearDown(self):
    #     self.req_ctx.pop()
    #     super(NoticeTestCase, self).tearDown()

    def test_reply_related(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        u3 = self.commit_user(name='user3')
        with self.app.test_request_context():
            # u3 follow u1, u2
            self.login_user(username=u3.username)
            self.post_to(url_for('api.follow'), dict(type='user', id=1))
            self.post_to(url_for('api.follow'), dict(type='user', id=2))
            self.log_out()

            # u1 post topic
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            self.log_out()

            # u2 reply to topic of u1, mention u3
            self.login_user(username=u2.username)
            self.commit_reply(1, u'@user3 抢沙发🐶')
            # u2 self upvote reply
            self.post_to(url_for('api.upvote'), dict(type='reply', id=1))
            # u2 self upvote should not get notice
            resp = self.client.get(url_for('notice.index'))
            self.assertNotIn('notice-dot', self.as_text(resp))
            self.log_out()

            # u1 upvote reply of u2
            self.login_user(username=u1.username)
            self.post_to(url_for('api.upvote'), dict(type='reply', id=1))
            resp = self.client.get(url_for('notice.index'))
            # u2 new reply notice
            self.assertIn(u2.username, self.as_text(resp))
            self.assertIn(u'回复了你的主题', self.as_text(resp))
            self.log_out()

            # mock async add notice and pop context
            sleep(2)
            db.session.close()

            # u2 should get u1 upvote reply notice
            self.login_user(username=u2.username)
            resp = self.client.get(url_for('notice.index'))
            self.assertIn('notice-dot', self.as_text(resp))
            self.assertIn(u1.username, self.as_text(resp))
            self.assertIn(u'赞了你的回复', self.as_text(resp))
            self.log_out()

            # u 3 check two notice
            self.login_user(username=u3.username)
            resp = self.client.get(url_for('notice.index'))
            self.assertIn(u1.username, self.as_text(resp))
            self.assertIn(u'发表了主题', self.as_text(resp))
            self.assertIn(u'赞了回复', self.as_text(resp))
            self.assertIn(u2.username, self.as_text(resp))
            self.assertIn(u'回复了主题', self.as_text(resp))
            self.assertIn(u'提到了你', self.as_text(resp))
            # print self.as_text(resp).encode('utf-8')

    def test_topic_related(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        u3 = self.commit_user(name='user3')
        with self.app.test_request_context():
            # u1 post topic
            self.login_user(username=u1.username)
            self.commit_topic(title='titletexthere', login=False)
            self.log_out()

            # u2 upvote, follow, bookmark topic of u1
            self.login_user(username=u2.username)
            self.post_to(url_for('api.follow'), dict(type='topic', id=1))
            self.post_to(url_for('api.bookmark'), dict(type='topic', id=1))
            self.post_to(url_for('api.upvote'), dict(type='topic', id=1))
            self.log_out()

            # u3 post reply
            self.login_user(username=u3.username)
            self.commit_reply(1, u'抢沙发!!!🐶')
            self.log_out()

            self.login_user(username=u2.username)
            sleep(2)
            db.session.close()

            # u2 should get u3 reply notice
            resp = self.client.get(url_for('notice.index'))
            self.assertIn(u3.username, self.as_text(resp))
            self.assertIn(u'回复了主题', self.as_text(resp))
            self.log_out()

            # u1 should get u2, u3 actions notice
            self.login_user(username=u1.username)
            resp = self.client.get(url_for('notice.index'))
            self.assertIn(u2.username, self.as_text(resp))
            self.assertIn(u3.username, self.as_text(resp))
            self.assertIn(u'回复了', self.as_text(resp))
            self.assertIn(u'赞了', self.as_text(resp))
            self.assertIn(u'关注了', self.as_text(resp))
            self.assertIn(u'收藏了', self.as_text(resp))

    def test_user_related(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        u3 = self.commit_user(name='user3')
        with self.app.test_request_context():
            # u1 follow u2
            self.login_user(username=u1.username)
            self.post_to(url_for('api.follow'), dict(type='user', id=2))
            self.log_out()

            # u2 follow u3
            self.login_user(username=u2.username)
            self.post_to(url_for('api.follow'), dict(type='user', id=3))
            self.log_out()

            # u1 should get notice
            self.login_user(username=u1.username)
            sleep(1)
            db.session.close()
            resp = self.client.get(url_for('notice.index'))
            self.assertTrue('user2' in self.as_text(resp))
            self.assertTrue(u'关注了' in self.as_text(resp))
            self.assertTrue('user3' in self.as_text(resp))

if __name__ == '__main__':
    unittest.main()
