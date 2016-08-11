# coding: utf-8
from flask import Blueprint, render_template, current_app, redirect, url_for, \
            g, flash
from datetime import datetime, timedelta


home = Blueprint('index', __name__,
                 static_folder='../static',
                 template_folder='../templates/home')


@home.route('/')
def frontpage():
    # return render_template('index.html')
    return redirect(url_for('topic.index'))


@home.app_errorhandler(404)
def handle404(e):
    return render_template('404.html'), 404


@home.app_errorhandler(403)
def handle404(e):
    return render_template('403.html'), 403


@home.app_errorhandler(500)
def handle404(e):
    return render_template('500.html'), 500
