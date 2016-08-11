# coding: utf-8
import unittest
from time import sleep
from flask import url_for, session
from sayit.models import UserRole, Topic, Node
from sayit.exts import db
from base_setup import BaseSetup


class UserTestCase(BaseSetup):
    def counter_html_str(self, _type, user, number):
        d = {
            'topic': '<a class="topic-number" href="/user/{0}?tab=topic">{1}</a>',
            'reply': '<a class="reply-number" href="/user/{0}?tab=reply">{1}</a>',
            'follower':  '<a class="follower-number" href="/user/{0}?tab=follower">{1}</a>',
            'follow': '<a class="follow-number" href="/user/{0}?tab=following">{1}</a>',
        }
        return d[_type].format(user.username, number)

    def test_topic_related(self):
        user = self.commit_user()
        with self.app.test_request_context():
            # 0主题
            resp = self.client.get(url_for('user.view_user',
                                           username=user.username,
                                           tab='topic'))
            # print self.as_text(resp).encode('utf-8')
            a_tag = self.counter_html_str('topic', user, 0)
            self.assertIn(a_tag, self.as_text(resp))
            self.assertTrue(u'没有记录' in self.as_text(resp))
            self.login_user(user.username)
            # 3主题
            for i in range(3):
                self.commit_topic('titlegoeshere{0}'.format(i), login=False)
            # need to wait async incr counter task done
            sleep(5)
            resp = self.client.get(url_for('user.view_user',
                                           username=user.username,
                                           tab='topic'))
            a_tag = self.counter_html_str('topic', user, 3)
            self.assertIn(a_tag, self.as_text(resp))
            for i in range(3):
                self.assertTrue(
                    'titlegoeshere{0}'.format(i) in self.as_text(resp))

    def test_reply_relate(self):
        user = self.commit_user()
        with self.app.test_request_context():
            self.login_user(user.username)
            resp = self.client.get(url_for('user.view_user',
                                           username=user.username,
                                           tab='reply'))
            self.commit_topic('thisistitle~~~~', login=False)
            a_tag = self.counter_html_str('reply', user, 0)
            self.assertIn(a_tag, self.as_text(resp))
            self.assertTrue(u'没有记录' in self.as_text(resp))
            topic = Topic.query.get(1)
            for i in range(3):
                self.commit_reply(topic.id, content='replycontent{0}'.format(i))
            resp = self.client.get(url_for('user.view_user',
                                           username=user.username,
                                           tab='reply'))
            for i in range(3):
                self.assertTrue(
                    'replycontent{0}'.format(i) in self.as_text(resp))

    def test_button_render(self):
        u1 = self.commit_user(name='user1')
        u2 = self.commit_user(name='user2')
        block = u'<span>屏蔽</span>'
        follow = u'<span>关注</span>'
        with self.app.test_request_context():
            # 未登录不显示
            resp = self.client.get(url_for('user.view_user',
                                           username=u1.username))
            self.assertNotIn(block, self.as_text(resp))
            self.assertNotIn(follow, self.as_text(resp))

            # 登录u1
            self.login_user(u1.username)
            resp = self.client.get(url_for('user.view_user',
                                           username=u1.username))
            # 自己不显示
            self.assertNotIn(block, self.as_text(resp))
            self.assertNotIn(follow, self.as_text(resp))

            # 查看u2
            resp = self.client.get(url_for('user.view_user',
                                           username=u2.username))
            self.assertIn(block, self.as_text(resp))
            self.assertIn(follow, self.as_text(resp))

    def test_index_render(self):
        user = self.commit_user()
        resp = self.client.get(url_for('user.view_user',
                                       username=user.username))
        self.assertIn(user.username, self.as_text(resp))
        self.assertIn(u'未选择分类标签', self.as_text(resp))

        resp = self.client.get(url_for('user.view_user',
                                       username='notexistuser'))
        self.assertTrue(resp.status_code == 404)

if __name__ == '__main__':
    unittest.main()
