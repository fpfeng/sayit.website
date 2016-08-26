import re
from flask import Blueprint, render_template, g, request, jsonify, abort
from flask_login import login_required
from ..g_func import user_and_session
from ..models import User, Topic, UserUpvoteReply, get_or_create, Reply, \
         UserFollowTopic, UserUpvoteTopic, UserFollowUser, UserBlockUser, \
         UserBookmarkTopic
from ..util.send_email import create_send_email
from ..redis_ugly_wrap import id_is_exist, single_asso_key, counter_switch, \
        get_all_username_list, check_mailto_limit, oppsite_user_switch


api = Blueprint('api', __name__)

api.before_request(user_and_session)


@api.route('/')
def index():
    abort(404)


def db_toggle(session, model, **kwargs):
    success = False
    row, exist = get_or_create(session,
                               model,
                               **kwargs)
    if not exist:
        session.add(row)
    else:
        row.is_cancel = not(bool(row.is_cancel))

    try:
        session.commit()
        success = True
    except:
        session.rollback()
    finally:
        return success


def db_switch(session, table, action, uid, xid):
    topic_models = {
        'bookmark': UserBookmarkTopic,
        'follow': UserFollowTopic,
        'upvote': UserUpvoteTopic,
    }
    user_models = {
        'follow': UserFollowUser,
        'block': UserBlockUser,
    }
    if table == 'reply':
        success = db_toggle(session, UserUpvoteReply, uid=uid, rid=xid)
    elif table == 'topic':
        success = db_toggle(session, topic_models[action], uid=uid, tid=xid)
    elif table == 'user':
        assert uid != int(xid)  # block user action on self
        success = db_toggle(session, user_models[action], uid=uid, act_on_uid=xid)
    return success


@api.route('/elite_or_pin', methods=['POST'])
@login_required
def elite_pin():
    if g.user.is_admin:
        action = request.form['action']
        tid = request.form['tid']

        attr = 'is_' + action
        editor_attr = action + '_edit_uid'
        topic = Topic.query.get(tid)
        current_stat = bool(getattr(topic, attr))
        setattr(topic, attr, not(current_stat))
        setattr(topic, editor_attr, g.user.id)
        try:
            g.session.commit()
            return jsonify({}), 200
        except Exception as e:
            g.session.rollback()
            return jsonify({'error': str(e)}), 404


@api.route('/users.json')
@login_required
def user_json():
    return jsonify(get_all_username_list())


@api.route('/upvote', methods=['POST'], endpoint='upvote')
@api.route('/bookmark', methods=['POST'], endpoint='bookmark')
@api.route('/follow', methods=['POST'], endpoint='follow')
@api.route('/block', methods=['POST'], endpoint='block')
@login_required
def action_dealer():
    action = request.endpoint.replace('api.', '')
    _type = request.form['type']
    _id = request.form['id']
    id_exist = id_is_exist(_id, _type)

    if id_exist:
        success = db_switch(g.session, _type, action, g.user.id, _id)
        if success:
            if action == 'follow':
                if _type == 'user':
                    oppsite_user_switch(g.user.id, _id)
            key = single_asso_key(g.user.id, _type, action)
            status = counter_switch(_id, _type, action, key, g.user.id)
            if action == 'block':  # keep private always return 1
                status['current'] = 1
        return jsonify(status)
    abort(404)


@api.route('/edit_email', methods=['POST'])
@login_required
def edit_email():
    if not g.user.email_confirmed:
        address = request.form['address']
        if re.match(r'[^@]+@[^@]+\.[^@]+', address):
            u = User.query.filter_by(email=address).first()
            if not u or g.user.id == u.id:
                is_reach = check_mailto_limit(g.user.id)
                if not is_reach:
                    create_send_email('confirm', address)
                    stat = 'send'
                else:
                    stat = 'limit'
            else:
                stat = 'exist'
            return jsonify({'status': stat}), 200


@api.route('/delete', methods=['POST'])
@login_required
def delete_post():
    _type = request.form['type']
    _id = request.form['id']

    assert _type in ['reply', 'topic']

    row = g.session.query(globals()[_type.title()]).get(_id)
    if row:
        if row.author.id == g.user.id or g.user.is_admin:
            row.is_delete = 1
            row.delete_uid = g.user.id
            g.session.commit()
            return jsonify({}), 200
    abort(404)
