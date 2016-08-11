# coding: utf-8
from flask_wtf import Form
from wtforms import BooleanField, StringField, PasswordField,\
        SubmitField, SelectField, TextAreaField, IntegerField
from flask_wtf.file import FileField, FileAllowed
from wtforms.fields.html5 import EmailField, URLField
from wtforms.validators import DataRequired, Length, Regexp, Email, url, \
    Optional, EqualTo, ValidationError
from wtforms.widgets import TextArea
from redis_ugly_wrap import get_child_node_id


W_ONLY = u'只允许英文字母和数字'


def _msg(min_, max_):
    return u'限制{0}到{1}个字符'.format(min_, max_)


class EmailForm(Form):
    email = EmailField('Email', validators=[
                                DataRequired(message=u'未输入'),
                                Email(message=u'不正确的地址')])


class CaptchaForm(Form):
    captcha = StringField(u'右侧验证码 点击图片刷新', validators=[
                          DataRequired(),
                          Length(min=5, max=5)])


class RecoverForm(EmailForm, CaptchaForm):
    pass


class PasswordForm(Form):
    password = PasswordField(u'密码', validators=[
        Regexp(r'^[\x00-\x7F]+$', message=u'仅限英文字母数字字符'),
        Length(min=6, max=30, message=_msg(6, 30)),
        EqualTo('confirm_password', message=u'两次输入的密码不一样')
    ])
    confirm_password = PasswordField(u'再次输入密码 确认无误')


class NewPasswordForm(PasswordForm):
    current = PasswordField(u'旧密码', validators=[
                            DataRequired(message=u'输入旧密码'),
                            Length(min=6, max=30, message=_msg(6, 30))
                            ])


class UserNameForm(Form):
    username = StringField(u'用户名', validators=[Regexp(
                                    r'^[a-zA-Z0-9]{4,15}$',
                                    message=W_ONLY + ' ' + _msg(4, 15)
                                    )])


class SignUpForm(UserNameForm, PasswordForm, EmailForm, CaptchaForm):
    email_private = BooleanField(u'不公开 Email')


class SignInForm(UserNameForm):
    password = PasswordField(u'密码', validators=[
                                    Length(min=6, max=30, message=_msg(6, 30))
                                            ])
    remember_me = BooleanField(u'记住我的登录状态')


class TopicForm(Form):
    node = StringField(u'节点', [DataRequired(message=u'未选择节点')])
    title = StringField(u'这里填写标题', validators=[
                                    Length(min=2, max=30, message=_msg(2, 30))
                        ])
    content = TextAreaField(u'正文', validators=[
                                Length(min=5, max=5000, message=_msg(5, 5000))
                                            ])

    def validate_node(form, field):
        node_id = field.data
        child_ids = get_child_node_id()
        if int(node_id) not in child_ids:
            raise ValidationError(message=u'无效节点ID')


class ReplyForm(Form):
    content = TextAreaField(u'正文', validators=[
                                Length(min=4, max=1000, message=_msg(4, 5000))
                                            ])


class EditAccountForm(Form):
    avatar = FileField(u'头像', validators=[
                            FileAllowed(['png', 'jpg'], u'仅支持png和jpg扩展名')
                                            ])
    email = EmailField('Email', validators=[])
    email_private = BooleanField(u'不公开 Email')
    city = StringField(u'中文填写', validators=[
                                    Length(max=50, message=_msg(1, 50))
                                            ])
    company = StringField('', validators=[
                                    Length(max=50, message=_msg(1, 50))
                                            ])
    github = StringField(u'帐号', validators=[
                                    Length(max=50, message=_msg(1, 50))
                                            ])
    website = URLField('http(s)://...', validators=[
                                                Optional(),
                                                url(message=u'不是有效 url')
                                                    ])
