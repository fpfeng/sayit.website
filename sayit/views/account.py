# coding: utf-8
from StringIO import StringIO
from flask import Blueprint, render_template, current_app, redirect, url_for, \
            g, flash, request, abort, send_file, session
from werkzeug.utils import secure_filename
from sqlalchemy.orm.exc import NoResultFound
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, login_required, current_user
from ..forms import SignUpForm, SignInForm, EditAccountForm, NewPasswordForm, \
        RecoverForm, PasswordForm
from ..models import User
from ..exts import db, login_manager, qniu
from ..util.safe_token import parse_email_address, parse_auth_data
from ..util.send_email import create_send_email
from ..util.save_avatar import save_then_upload
from ..util.simple_captcha import get_captcha
from ..redis_ugly_wrap import check_token_valid, mark_token_used


account = Blueprint('account', __name__, template_folder='../templates/account')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@login_manager.token_loader
def load_token(token):
    data = parse_auth_data(token)
    if data:
        user = User.query.get(data[0])
        if user and data[1] == user.password_hash:
            return user
        return None


@account.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    form = SignUpForm()
    if form.validate_on_submit():
        captcha = form.captcha.data
        if captcha == session['captcha']:
            exist, error_msg = check_input_data_exist(form)
            if not exist:
                email_private = 1 if request.form.get('email_private') else 0
                new_user = User(username=form.username.data,
                                email=form.email.data,
                                password=form.password.data,
                                email_private=email_private)
                db.session.add(new_user)
                db.session.commit()
                create_send_email('confirm', new_user.email)
                login_user(new_user, remember=True)
                flash(u'注册成功，按照邮件指示激活帐号后即可发帖！', 'success')
                return go_index()
            else:
                flash(error_msg, 'danger')
    return render_template('sign_up.html', form=form)


@account.route('/captcha')
def create_captcha():
    output = StringIO()
    img, numbers = get_captcha()
    img.save(output, 'JPEG', qulity=100)
    output.seek(0)
    session['captcha'] = numbers
    return send_file(output, mimetype='image/jpeg')


@account.route('/reset/<token>', methods=['POST', 'GET'])
def reset_password(token):
    not_use_before, email = check_token_valid(token)
    user = User.query.filter_by(email=email).first()
    if user and not_use_before:
        form = PasswordForm()
        if form.validate_on_submit():
            user.password = form.password.data
            db.session.commit()
            mark_token_used(token)
            flash(u'密码已更改', 'success')
            return redirect(url_for('.sign_in'))
        return render_template('reset_password.html', form=form)
    flash(u'该链接已失效，你可以再次请求重置', 'danger')
    return redirect(url_for('.recover'))


@account.route('/recover', methods=['GET', 'POST'])
def recover():
    if current_user.is_authenticated:
        return redirect(url_for('.edit'))
    else:
        form = RecoverForm()
        if form.validate_on_submit():
            captcha = form.captcha.data
            if captcha == session['captcha']:
                email = form.email.data
                exist = User.query.filter_by(email=email).scalar()
                if exist:
                    create_send_email('reset', email)
                    flash(u'邮件已发送！请查看操作指示', 'success')
                    return redirect(url_for('topic.index'))
                else:
                    flash(u'没有该Email的纪录', 'danger')
            else:
                flash(u'验证码错误', 'danger')
            return redirect(url_for('.recover'))
        return render_template('recover_password.html', form=form)


@account.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = parse_email_address(token)
        user = User.query.filter_by(email=email).one()
        if not user.email_confirmed:
            user.set_verify_role()
            db.session.commit()
            flash(u'帐号激活成功！', 'success')
        else:
            flash(u'你的帐号之前就激活了', 'warning')
    except:
        flash(u'无效链接', 'danger')
    return go_index()


@account.route('/sign_in', methods=['GET', 'POST'])
def sign_in():
    if current_user.is_authenticated:
        return go_index()

    form = SignInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if user.password_is_correct(form.password.data):
                remember = True if request.form.get('remember_me') else False
                login_user(user, remember=remember)
                _next = request.args.get('next')
                flash(u'你现在登录了', 'success')
                return redirect(_next) if _next else go_index()
            else:
                flash(u'密码错误', 'danger')
        else:
            flash(u'没有该用户的记录', 'danger')
    return render_template('sign_in.html', form=form)


@account.route('/sign_out')
@login_required
def sign_out():
    logout_user()
    flash(u'你已经退出了', 'warning')
    return go_index()


@account.route('/edit', methods=['POST', 'GET'])
@login_required
def edit():
    passwd = NewPasswordForm()
    passwd.password.label.text = u'新密码'
    passwd.confirm_password.label.text = u'再次输入新密码'

    profile = EditAccountForm()
    fields = ['email', 'email_private', 'city', 'company', 'website', 'github']

    _type = request.args.get('type')

    if _type == 'profile':
        if profile.validate_on_submit():
            filename = getattr(profile.avatar.data, 'filename')
            if filename:
                filename = replace_uid(secure_filename(filename))
                save_then_upload(filename, profile.avatar.data.read())

            fields.remove('email')  # email change in other way
            for f in fields:
                setattr(current_user, f, profile[f].data)
            flash(u'资料已更改', 'success')
            return commit_go_index()

    elif _type == 'password':
        if passwd.validate_on_submit():
            if current_user.password_is_correct(passwd.current.data):
                current_user.password = passwd.password.data
                flash(u'密码已更改', 'success')
            else:
                flash(u'旧密码验证失败', 'danger')
            return commit_go_index()
    for f in fields:
        value = getattr(current_user, f)
        if value != '0':
            setattr(profile[f], 'data', value)

    return render_template('edit_account.html', profile=profile, passwd=passwd)


def commit_go_index():
    db.session.commit()
    return redirect(url_for('.edit'))


def replace_uid(filename):
    return str(current_user.id) + filename[-4:]


def go_index():
    return redirect(url_for('topic.index'))


def query_exist(column, value):
    exist = False
    attr = getattr(User, column)
    q = db.session.query(User).filter(attr == value).first()
    if q:
        exist = True
    return exist


def check_input_data_exist(form):
    exist = False
    msg = None
    username_exist = query_exist('username', form.username.data)
    email_exist = query_exist('email', form.email.data)

    if username_exist and email_exist:
        msg = u'用户名和 Email 都'
    elif username_exist:
        msg = u'用户名'
    elif email_exist:
        msg = u'Email'

    if msg:
        exist = True
        msg += u'已存在记录'
    return exist, msg
