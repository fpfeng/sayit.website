# coding: utf-8
from flask import current_app, url_for, render_template
from flask_mail import Message
from .safe_token import create_email_token
from ..exts import mail, celery


@celery.task(bind=True, max_retries=5, default_retry_delay=60)
def async_email(self, msg):
    try:
        with current_app._get_current_object().app_context():
            mail.send(msg)
    except Exception as exc:
        raise self.retry(exc=exc)


def send_email(title, address, html):
    msg = Message(title,
                  sender=(
                    current_app.config.get('SITE_NAME'), 'admin@sayit.website'
                    ),
                  recipients=[address])
    msg.html = html
    async_email.apply_async(args=[msg])


def create_send_email(action, address):
    if action == 'confirm':
        text = u'请你打开以下链接激活帐号：'
        endpoint = 'account.confirm_email'
        title = u'激活帐号'
    elif action == 'reset':
        text = u'有人（希望是你）请求重置密码，请打开以下链接继续操作或者忽略本邮件。'
        endpoint = 'account.reset_password'
        title = u'重置密码'
    url = url_for(endpoint,
                  token=create_email_token(address),
                  _external=True)
    html = render_template('email.html', text=text, confirm_url=url)
    send_email(title, address, html)
