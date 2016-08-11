from sqlalchemy.orm.exc import NoResultFound
from celery.signals import task_postrun
from ..exts import db, celery
from ..models import User, Reply, Topic, get_or_create, UserNotice
from ..redis_ugly_wrap import incr_unread_count, get_user_asso_ids,\
    incr_post_count, user_unread_notice_count, reset_notice_count,\
    get_clicked_topic, topic_click_count


@celery.task(name='save_topic_click')
def save_click():
    topic_ids = get_clicked_topic()
    for tid in topic_ids:
        num = topic_click_count(tid)
        db.session.query(Topic).filter_by(id=tid).update({'click_count': num})
    db.session.commit()


@task_postrun.connect
def must_exit_session(*args, **kwargs):
    db.session.close()
    # db.session.remove()


@celery.task()
def mark_notice_read(uid):
    user = db.session.query(User).get(uid)
    if int(user_unread_notice_count(user)) > 0:
        for n in user.r_notices.filter_by(is_read=0).all():
            n.is_read = 1
        reset_notice_count(uid)


@celery.task()
def async_mention(to_users, from_uid, topic_id, reply_id):
    notice_rows = []
    for name in to_users:
        try:
            target = User.query.filter_by(username=name).one()
            new = UserNotice(notice_type='mention',
                             from_uid=from_uid,
                             to_uid=target.id,
                             notice_releate_id=topic_id,
                             reply_id=reply_id)
            notice_rows.append(new)
        except NoResultFound:
            continue
    commit_db(notice_rows)


def async_notice(n_type, from_uid, to_uid, notice_releate_id=0, reply_id=0):
    if from_uid != to_uid:
        row, exist = get_or_create(db.session,
                                   UserNotice,
                                   notice_type=n_type,
                                   from_uid=from_uid,
                                   to_uid=to_uid,
                                   notice_releate_id=notice_releate_id,
                                   reply_id=reply_id)
        if not exist:
            commit_db([row])


def notice_user_follower(notice_type, from_uid, notice_releate_id=0, reply_id=0):
    user = User.query.get(from_uid)
    full_type = 'follow_' + notice_type
    follower_uids = get_user_asso_ids(user, 'user')['user:follower']
    exclude_id = None
    if notice_type == 'upvote_reply':  # reply owner in follower list
        exclude_id = Reply.query.\
                            with_entities(Reply.user_id).\
                            filter_by(id=reply_id).\
                            first()[0]
    elif notice_type in ['follow_topic',
                         'bookmark_topic',
                         'upvote_topic',
                         'new_reply']:  # topic owner in follower list
        exclude_id = Topic.query.\
                            with_entities(Topic.user_id).\
                            filter_by(id=notice_releate_id).\
                            first()[0]
    elif notice_type == 'follow_user':  # following user in follower list
        exclude_id = notice_releate_id
    for uid in follower_uids:
        if uid != exclude_id:
            async_notice(full_type, from_uid, uid, notice_releate_id, reply_id)


def notice_topic_follower(topic_id, reply_id):
    topic = Topic.query.get(topic_id)
    author_id = Reply.query.\
        with_entities(Reply.user_id).\
        filter_by(id=reply_id).\
        first()[0]
    for row in topic.follow_users.all():
        if row.uid != topic.user_id and row.uid != author_id:
            async_notice('follow_topic_reply', author_id, row.uid, topic_id, reply_id)


def get_user(uid):
    return User.query.get(uid)


@celery.task()
def upvote_reply(uid, rid):
    notice_type = 'upvote_reply'
    reply = Reply.query.get(rid)
    async_notice(notice_type, uid, reply.user_id, reply.topic_id, rid)
    if uid != reply.user_id:
        notice_user_follower(notice_type, uid, reply.topic_id, rid)


@celery.task()
def new_reply(reply_uid, topic_uid, topic_id, reply_id):
    notice_type = 'new_reply'
    async_notice(notice_type, reply_uid, topic_uid, topic_id, reply_id)
    notice_user_follower(notice_type, reply_uid, topic_id, reply_id)
    notice_topic_follower(topic_id, reply_id)
    incr_post_count(get_user(reply_uid), 'reply')


@celery.task()
def user_to_topic(_type, from_uid, tid):
    topic = db.session.query(Topic).get(tid)
    if topic.user_id != from_uid:
        async_notice(_type, from_uid, topic.user_id, topic.id)
    notice_user_follower(_type, from_uid, tid)


@celery.task()
def user_to_user(_type, from_uid, to_uid):
    async_notice(_type, from_uid, to_uid)
    notice_user_follower(_type, from_uid, to_uid)


@celery.task()
def new_topic(author_uid, tid):
    notice_user_follower('new_topic', author_uid, tid)
    incr_post_count(get_user(author_uid), 'topic')


def user_mention(to_users, from_name, from_uid, topic_id, reply_id=0):
    to_users = set(to_users)
    while from_name in to_users:
        to_users.remove(from_name)
    if to_users:
        async_mention.delay(to_users, from_uid, topic_id, reply_id)


def commit_db(rows):
    try:
        db.session.add_all(rows)
        db.session.commit()
        for r in rows:
            incr_unread_count(r.to_uid)
    except:
        raise
        db.session.rollback()
