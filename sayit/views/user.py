from functools import partial
from flask import Blueprint, render_template, url_for, g, abort, redirect, \
        request
from flask_login import current_user, login_required
from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from ..models import User, Topic, Reply, UserFollowTopic, UserFollowUser
from ..g_func import user_and_session
from ..redis_ugly_wrap import get_user_page_info, get_node_names

user = Blueprint('user', __name__, template_folder='../templates/user')

user.before_request(user_and_session)


@user.route('/')
def index():
    return redirect(url_for('topic.index'))


def query_rows(tab, **kwargs):
    models = {
        'topic': Topic,
        'reply': Reply,
        'bookmark': UserFollowTopic,
        'follower': UserFollowUser,
        'following': UserFollowUser,
    }
    return models[tab].query.filter_by(**kwargs)


@user.route('/<username>')
def view_user(username):
    try:
        user = User.query.filter_by(username=username).one()

        page = request.args.get('page', 1, type=int)
        tab = request.args.get('tab', type=str)

        tab_rows = None
        paginate = None
        rows = None

        query = partial(query_rows, tab)

        if tab == 'topic':
            tab_rows = query(user_id=user.id, is_delete=0)
        elif tab == 'reply':
            tab_rows = query(user_id=user.id, is_delete=0)
        elif tab == 'bookmark':
            tab_rows = query(uid=user.id, is_cancel=0)
        elif tab == 'follower':
            tab_rows = query(act_on_uid=user.id, is_cancel=0)
        elif tab == 'following':
            tab_rows = query(uid=user.id, is_cancel=0)

        if tab_rows:
            paginate = tab_rows.paginate(page, 30)
            rows = paginate.items

        asso_ids, counts = get_user_page_info(user, g.user)
        return render_template('view_user.html',
                               user=user,
                               asso_ids=asso_ids,
                               counts=counts,
                               paginate=paginate,
                               rows=rows,
                               node_names=get_node_names())
    except NoResultFound:
        abort(404)
