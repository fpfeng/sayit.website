# coding: utf-8
import unittest
from time import sleep
from flask import url_for, session
from sayit.models import UserRole, Topic, Node
from sayit.exts import db
from base_setup import BaseSetup


class TopicTestCase(BaseSetup):
    def test_try_new_topic(self):
        resp = self.client.get(url_for('topic.index'))
        self.assertTrue(u'登录发表' in self.as_text(resp))

        user = self.add_user()
        with self.app.test_request_context():
            self.login_user()
            resp = self.client.get(url_for('topic.index'))
            self.assertTrue(user.username in self.as_text(resp))

            resp = self.client.get(url_for('topic.new_topic'), follow_redirects=True)
            self.assertTrue(u'确认Email' in self.as_text(resp))

            user.set_ban_post_role()
            db.session.commit()
            resp = self.client.get(url_for('topic.new_topic'), follow_redirects=True)
            self.assertTrue(u'禁言' in self.as_text(resp))

            user.set_verify_role()
            db.session.commit()
            resp = self.client.get(url_for('topic.new_topic'))
            self.assertTrue(u'填写标题' in self.as_text(resp))

    def test_new_topic(self):
        user = self.add_user()
        user.set_verify_role()
        db.session.commit()
        with self.app.test_request_context():
            self.login_user()
            attr = self.topic_body()
            resp = self.client.post(url_for('topic.new_topic'),
                                    data=attr,
                                    follow_redirects=True)
            # single topic page
            node = Node.query.get(attr['node'])
            self.assertTrue(node.name in self.as_text(resp))
            self.assertTrue(attr['title'] in self.as_text(resp))
            self.assertTrue(attr['content'] in self.as_text(resp))

            resp = self.client.get(url_for('topic.index'), follow_redirects=True)
            self.assertTrue(attr['title'] in self.as_text(resp))
            # not exist topic
            resp = self.client.get(url_for('topic.single_topic', topic_id=99))
            self.assertTrue(resp.status_code == 404)

    def test_preview_post(self):
        user = self.add_user()
        user.set_verify_role()
        db.session.commit()
        with self.app.test_request_context():
            content = '```print topicontent```'
            self.login_user()
            resp = self.client.post(url_for('topic.preview_topic'),
                                    data={'md': content})
            as_dict = eval(self.as_text(resp))
            self.assertTrue('html' in as_dict)
            self.assertTrue('print topicontent' in as_dict['html'])

    def test_edit_topic(self):
        user = self.add_user()
        user.set_verify_role()
        with self.app.test_request_context():
            self.commit_topic()
            topic = Topic.query.filter().first()
            resp = self.client.get(url_for('topic.edit_topic', tid=topic.id))
            self.assertTrue(topic.content in self.as_text(resp))

            new = {
                'node': 102,
                'title': u'new内容content2😠测试test😊',
                'content': u'🐶🐱标题😠title😊12🐶🐱标题😠title😊12',
            }
            resp = self.client.post(url_for('topic.edit_topic', tid=topic.id),
                                    data=new,
                                    follow_redirects=True)

            node = Node.query.get(new['node'])
            self.assertTrue(node.name in self.as_text(resp))
            self.assertTrue(new['title'] in self.as_text(resp))
            self.assertTrue(new['content'] in self.as_text(resp))
            resp = self.client.get(url_for('topic.index'), follow_redirects=True)
            self.assertTrue(new['title'] in self.as_text(resp))

    def test_reply(self):
        user = self.add_user()
        newuser = self.commit_user()
        user.set_verify_role()
        topic = None
        with self.app.test_request_context():
            self.commit_topic()
            topic = Topic.query.filter().first()
            self.commit_reply(topic.id, u'抢沙发🐶🐱')
            self.client.get(url_for('account.sign_out'))
            self.login_user(newuser.username)
            self.commit_reply(topic.id, u'抢地板🐶🐱')
            resp = self.client.get(url_for('topic.single_topic', topic_id=topic.id))
            self.assertTrue(user.username in self.as_text(resp))
            self.assertTrue(u'抢沙发🐶🐱' in self.as_text(resp))
            self.assertTrue(newuser.username in self.as_text(resp))
            self.assertTrue(u'抢地板🐶🐱' in self.as_text(resp))
            # test redis click count
            # 1 for add post, 2 for 2 add reply, 1 for reply check, so 9 = 4 + 5 for loop
            for _ in range(5):
                self.client.get(url_for('topic.single_topic', topic_id=topic.id))
            resp = self.client.get(url_for('topic.index'))
            # print self.as_text(resp).encode('utf-8')
            self.assertTrue(u'click-count text-muted">9</span>'in self.as_text(resp))
            # test redis reply count
            self.assertTrue(u'class="reply-count">2</span>' in self.as_text(resp))

    def test_select_node_sift(self):
        user = self.commit_user()
        with self.app.test_request_context():
            self.login_user(user.username)
            self.commit_topic('first_post_topic', login=False)
            # mock post after 3 second
            sleep(3)
            self.commit_topic('second_post_topic', login=False)
            # 筛选最新
            resp = self.client.get(url_for('topic.index', sift='latest'))
            self.assertTrue(self.as_text(resp).index('first') >
                            self.as_text(resp).index('second'))
            # 筛选精华
            # t1 = Topic.query.filter().first()
            # t1.is_pin = 1  # 置顶
            topic2 = Topic.query.filter().all()[1]
            topic2.is_elite = 1  # 精华
            db.session.commit()
            resp = self.client.get(url_for('topic.index', sift='elite'))
            self.assertTrue('first_post' not in self.as_text(resp))
            self.assertTrue('second_post' in self.as_text(resp))
            # 筛选无人回复
            self.commit_reply(topic2.id, u'抢沙发🐶🐱')
            resp = self.client.get(url_for('topic.index', sift='noreply'))
            self.assertTrue('first_post' in self.as_text(resp))
            self.assertTrue('second_post' not in self.as_text(resp))
            # 浏览节点
            topic2.node_id = 103
            db.session.commit()
            resp = self.client.get(url_for('topic.index', node=103))
            self.assertTrue(u'子3' in self.as_text(resp))
            self.assertTrue('second_post' in self.as_text(resp))
            self.assertTrue('first_post' not in self.as_text(resp))

    def test_qiniu_related(self):
        user = self.add_user()
        user.set_verify_role()
        db.session.commit()
        with self.app.test_request_context():
            self.login_user()
            resp = self.client.get(url_for('topic.gen_qtoken'))
            as_dict = eval(self.as_text(resp))
            self.assertTrue('uptoken' in as_dict)

            resp = self.client.get(url_for('topic.gen_qkey'))
            as_dict = eval(self.as_text(resp))
            self.assertTrue('key' in as_dict)

            key = 'fakedate/' + as_dict['key'] + '.fake_extension'
            resp = self.client.post(url_for('topic.save_qkey'),
                                    data={'key': key, 'hash': '123'})
            self.assertTrue(resp.status_code == 200)

            key = 'fakedate/shouldget403error.fake_extension'
            resp = self.client.post(url_for('topic.save_qkey'),
                                    data={'key': 'notexist', 'hash': '123'})
            self.assertTrue(resp.status_code == 403)

if __name__ == '__main__':
    unittest.main()
