# coding: utf-8
import re
from datetime import datetime
from functools import partial
from flask import Blueprint, render_template, current_app, redirect, url_for, \
            g, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy.orm.exc import NoResultFound
from ..models import User, Topic, Node, Reply
from ..forms import TopicForm, ReplyForm
from ..util.async_task import user_mention
from ..util.md_html import to_html
from ..g_func import user_and_session
from ..redis_ugly_wrap import hset_topic_key, get_user_asso_ids, \
        get_page_counter, add_click_count, get_topic_field_count, \
        update_topic_cache, get_node_list, get_child_node_id, \
        user_can_post, add_user_post_count, site_stats, today_hottest,\
        get_node_names


topic = Blueprint('topic', __name__,  template_folder='../templates/topic')


topic.before_request(user_and_session)


@topic.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    nid = request.args.get('node', type=int)
    sift = request.args.get('sift', type=str)

    vaild_nodes = get_child_node_id()
    query = Topic.query.filter(Topic.is_delete == 0)

    node_name = None
    if nid in vaild_nodes:
        query = Topic.query.filter_by(node_id=nid)
        node_name = get_node_names()[nid]  # for page title

    chs = {
        'latest': u'最新创建',
        'elite': u'精华主题',
        'noreply': u'无人问津',
        }

    sift_name = None
    if sift == 'latest':
        query = query.filter().order_by(Topic.create_time.desc())
    elif sift == 'elite':
        query = query.filter_by(is_elite=1)
    elif sift == 'noreply':
        query = query.filter(~Topic.replies.any())
    else:
        query = query.order_by(Topic.is_pin.desc()).\
                    order_by(Topic.is_elite.desc()).\
                    order_by(Topic.last_reply_time.desc())

    sift_name = chs.get(sift)

    t_paginate = query.paginate(page, current_app.config['TOPICS_PER_PAGE'])
    topics = t_paginate.items

    asso_ids = None
    if g.user.is_authenticated:
        asso_ids = get_user_asso_ids(g.user, 'topic')

    return render_template('topics_list.html',
                           paginate=t_paginate,
                           topics=topics,
                           nodes=get_node_list(),
                           asso_ids=asso_ids,
                           node_name=node_name,
                           sift_name=sift_name,
                           sifts=chs,
                           stats=site_stats(),
                           hottest=today_hottest())


@topic.route('/<int:topic_id>')
@topic.route('/<int:topic_id>/add_reply', methods=['POST'], endpoint='add_reply')
def single_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)

    if not topic.is_delete or topic.is_delete and g.user.is_admin:
        reply = ReplyForm()

        if reply.validate_on_submit() and user_can_post(g.user, 'reply'):
            html, users = get_html_and_users(reply.content.data)
            current_floor = int(get_topic_field_count(topic.id, 'reply')) + 1
            new = Reply(user_id=g.user.id,
                        content=reply.content.data,
                        content_html=html,
                        current_floor=current_floor)
            topic.replies.append(new)
            topic.last_reply_time = datetime.now()
            g.session.commit()
            update_topic_cache(topic.id,
                               new.create_time,
                               g.user)
            add_user_post_count(g.user, 'reply')
            user_mention(users, g.user.username, g.user.id, topic_id, new.id)
            return redirect(url_for('.single_topic', topic_id=topic.id))

        counts = get_page_counter(topic, 'topic')
        add_click_count(topic)

        asso_ids = None
        if g.user.is_authenticated:
            asso_ids = get_user_asso_ids(g.user, 'topic')

        editable = check_can_edit(topic.user_id, topic.create_time)
        return render_template('single_topic.html',
                               topic=topic,
                               form=reply,
                               counts=counts,
                               asso_ids=asso_ids,
                               editable=editable)
    abort(404)


def check_can_edit(tuid, create_time):
    now = datetime.now()
    diff = now - create_time
    editable = False
    if g.user.is_authenticated:
        if tuid == g.user.id \
            and diff.seconds < current_app.config.get('TOPIC_EDIT_EXPIRE', 300) \
                or g.user.is_admin:
            editable = True
    return editable


@topic.route('/<int:tid>/edit', methods=['GET', 'POST'])
@login_required
def edit_topic(tid):
    topic = Topic.query.get_or_404(tid)
    editable = check_can_edit(topic.user_id, topic.create_time)
    if g.user.is_admin or editable:
        form = TopicForm()

        fields = {
                    'node': 'node_id',
                    'title': 'title',
                    'content': 'content',
                }

        if form.validate_on_submit():
            html, users = get_html_and_users(form.content.data)
            for form_field, db_attr in fields.iteritems():
                setattr(topic, db_attr, form[form_field].data)
            topic.content_html = html

            now = datetime.now()
            topic.content_edit_time = unicode(now.replace(microsecond=0))
            topic.content_edit_uid = g.user.id
            g.session.commit()

            user_mention(users, g.user.username, g.user.id, topic.id)
            return redirect(url_for('.single_topic', topic_id=tid))

        for form_field, db_attr in fields.iteritems():
            setattr(form[form_field], 'data', getattr(topic, db_attr))

        return render_template('new_topic.html',
                               form=form,
                               tid=tid,
                               nodes=get_node_list())
    abort(403)


@topic.route('/new', methods=['GET', 'POST'])
@login_required
def new_topic():
    if user_can_post(g.user, 'topic'):
        form = TopicForm()
        if form.validate_on_submit():
            html, users = get_html_and_users(form.content.data)
            new = Topic(user_id=g.user.id,
                        node_id=form.node.data,
                        title=form.title.data,
                        content=form.content.data,
                        content_html=html)
            g.session.add(new)
            g.session.commit()
            user_mention(users, g.user.username, g.user.id, new.id)
            update_topic_cache(new.id,
                               new.create_time,
                               g.user,
                               is_reply=False)
            add_user_post_count(g.user, 'topic')
            return redirect(url_for('.single_topic', topic_id=new.id))
        return render_template('new_topic.html',
                               form=form,
                               nodes=get_node_list())
    else:
        if g.user.is_ban_post:
            flash(u'你已被禁言', 'warning')
        elif not g.user.email_confirmed:
            flash(u'确认Email后才能发帖', 'warning')
        else:
            flash(u'大哥不要灌水好吗', 'warning')
        return go_index()


def go_index():
    return redirect(url_for('.index'))


def get_html_and_users(content):
        linked_content, users = link_mention_floor_and_user(content)
        html = to_html(linked_content)
        return html, users


def extract_user(mention_users, match):
    url_base = url_for('user.index')
    mention_users.append(match.group(1))
    return '[@{0}]({1}{0}){2}'.format(match.group(1), url_base, match.group(2))


def link_mention_floor_and_user(content_text):
    """#x楼 @用户名"""
    mention_users = []

    link_floor = re.sub(ur'(?<!\S)#(\d+)\u697c(\s|$)',
                        ur'[#\1\u697c](#reply\1) ',
                        content_text)

    link_user = re.sub(ur'(?<!\S)@([A-Za-z0-9]{4,15})(\s|$)',
                       partial(extract_user, mention_users),
                       link_floor)

    return link_user, mention_users
