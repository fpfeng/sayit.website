from flask import Blueprint, render_template, g, request, current_app
from flask_login import login_required
from ..models import UserNotice
from ..g_func import user_and_session
from ..util.async_task import mark_notice_read
from .. import db

notice = Blueprint('notice', __name__, template_folder='../templates/notice')

notice.before_request(user_and_session)


@notice.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    # need pip install https://github.com/mitsuhiko/flask-sqlalchemy/pull/328
    # n_paginate = db.session.query(UserNotice).\
    #     filter_by(to_uid=g.user.id).\
    #     paginate(page, current_app.config.get(
    #                                     'NOTICES_PER_PAGE', 30))
    n_paginate = g.user.r_notices.paginate(page, current_app.config.get(
                                                    'NOTICES_PER_PAGE', 30))
    notices = n_paginate.items

    mark_notice_read.delay(g.user.id)
    return render_template('notices.html', paginate=n_paginate, notices=notices)
