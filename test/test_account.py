# coding: utf-8
import unittest
from StringIO import StringIO
from flask import url_for
from base_setup import BaseSetup
from sayit.exts import db
from sayit.models import User
from sayit.util.safe_token import create_email_token


class AccountTestCase(BaseSetup):
    def test_render(self):
        resp = self.client.get(url_for('account.sign_in'))
        self.assertTrue(u'帐号登录' in self.as_text(resp))

        resp = self.client.get(url_for('account.sign_up'))
        self.assertTrue(u'新帐号注册' in self.as_text(resp))

    def test_post_up_in_out(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['captcha'] = '12345'

            resp = c.post(url_for('account.sign_up'), data=dict(
                          username=self.username,
                          password=self.password,
                          confirm_password=self.password,
                          email=self.email,
                          captcha='12345',
                          ), follow_redirects=True)
            self.assertTrue(resp.status_code == 200)
            self.assertTrue(u'注册成功' in self.as_text(resp))

        resp = self.client.get(url_for('account.sign_in'), follow_redirects=True)
        # if user already login, redirect to topic index
        self.assertTrue(u'筛选' in self.as_text(resp))

        resp = self.client.get(url_for('account.sign_out'), follow_redirects=True)
        self.assertTrue(u'已经退出' in self.as_text(resp))

        resp = c.post(url_for('account.sign_up'), data=dict(
                          username='aotherone',
                          password=self.password,
                          confirm_password=self.password,
                          email=self.email,
                          captcha='12345',
                          ))
        self.assertTrue(u'Email已存在记录' in self.as_text(resp))

        resp = c.post(url_for('account.sign_up'), data=dict(
                          username=self.username,
                          password=self.password,
                          confirm_password=self.password,
                          email='another@example.com',
                          captcha='12345',
                          ))
        self.assertTrue(u'用户名已存在记录' in self.as_text(resp))

        resp = self.client.post(url_for('account.sign_in'), data=dict(
                                username=self.username,
                                password=self.password,
                                ), follow_redirects=True)
        self.assertTrue(u'你现在登录了' in self.as_text(resp))

    def test_sign_in_fail(self):
        resp = self.client.post(url_for('account.sign_in'), data=dict(
                                username='testuser',
                                password='testpassword',
                                ), follow_redirects=True)

        self.assertTrue(u'没有该用户的记录' in self.as_text(resp))

        db.session.add(self.add_user_row())
        db.session.commit()

        resp = self.client.post(url_for('account.sign_in'), data=dict(
                                username='testuser',
                                password='wrongpwd',
                                ), follow_redirects=True)

        self.assertTrue(u'密码错误' in self.as_text(resp))

    def test_confirm_email(self):
        token = create_email_token('test@example.com')
        resp = self.client.get(url_for('account.confirm_email', token=token), follow_redirects=True)
        self.assertTrue(u'无效链接' in self.as_text(resp))

        db.session.add(self.add_user_row())
        db.session.commit()

        token = create_email_token('test@example.com')
        resp = self.client.get(url_for('account.confirm_email', token=token), follow_redirects=True)
        self.assertTrue(u'帐号激活成功' in self.as_text(resp))

        resp = self.client.get(url_for('account.confirm_email', token=token), follow_redirects=True)
        self.assertTrue(u'之前就激活了' in self.as_text(resp))

    def test_recover_email(self):
        db.session.add(self.add_user_row())
        db.session.commit()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['captcha'] = '12345'

            resp = c.post(url_for('account.recover'), data=dict(
                                    email=self.email,
                                    captcha='12345'
                                    ), follow_redirects=True)
            self.assertTrue(u'邮件已发送' in self.as_text(resp))

    def test_recover_not_exist(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['captcha'] = '12345'
            resp = c.post(url_for('account.recover'), data=dict(
                                    email='notexist@test.com',
                                    captcha='12345'
                                    ), follow_redirects=True)
            self.assertTrue(u'没有该Email' in self.as_text(resp))

            # resp = c.post(url_for('account.recover'), data=dict(
            #                         email=self.email,
            #                         captcha='54321'
            #                         ), follow_redirects=True)
            # self.assertTrue(u'验证码错误' in self.as_text(resp))
    def test_rest_password(self):
        # invalid token
        resp = self.client.get(url_for('account.reset_password', token='??'))
        self.assertTrue(resp.status_code == 302)

        db.session.add(self.add_user_row())
        db.session.commit()

        token = create_email_token(self.email)

        resp = self.client.get(url_for('account.reset_password', token=token))
        self.assertTrue(resp.status_code == 200)

        resp = self.client.post(url_for('account.reset_password',
                                        token=token), data=dict(
                                            password='newpassword',
                                            confirm_password='newpassword'
                                        ), follow_redirects=True)
        self.assertTrue(u'密码已更改' in self.as_text(resp))

        # used token act like invalid token
        resp = self.client.get(url_for('account.reset_password', token=token))
        self.assertTrue(resp.status_code == 302)

    def test_edit_profile(self):
        db.session.add(self.add_user_row())
        db.session.commit()

        attrs = {
            'city': 'where',
            'avatar': (StringIO('fake image content'), 'fake.png'),
            'company': 'which',
            'website': 'https://why.com',
            'github': 'what'
            }

        self.client.post(url_for('account.sign_in'), data=dict(
                                username=self.username,
                                password=self.password,
                                ), follow_redirects=True)

        resp = self.client.post(url_for('account.edit', type='profile'),
                                data=attrs,
                                follow_redirects=True)
        self.assertTrue(u'资料已更改' in self.as_text(resp))

        newpwd = 'changepasswd'
        resp = self.client.post(url_for('account.edit', type='password'),
                                data=dict(current=self.password,
                                          password=newpwd,
                                          confirm_password=newpwd),
                                follow_redirects=True)
        self.assertTrue(u'密码已更改' in self.as_text(resp))

        del attrs['avatar']
        u = User.query.filter().first()
        for k, v in attrs.iteritems():
            self.assertEqual(getattr(u, k), v)
        self.assertEqual(u.email_private, 0)
        self.assertTrue(u.password_is_correct(newpwd))

if __name__ == '__main__':
    unittest.main()
