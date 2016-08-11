# coding: utf-8
from datetime import datetime
from .redis_ugly_wrap import user_unread_notice_count, reply_upvote_count, \
            topics_list_cached_count, get_topic_last_reply_info, get_node_names, \
            user_can_post


def add_delimiter(text):
    return text + u' · '


def get_reply_upvote_count(reply):
    return reply_upvote_count(reply)


def user_unread_count(user):
    return user_unread_notice_count(user)


def topic_cached_count(topic, field):
    return topics_list_cached_count(topic, field)


def check_can_post(user, _type):
    return user_can_post(user, _type)


def topic_last_reply(topic):
    t = get_topic_last_reply_info(topic.id)
    return t


def node_name(nid):
    return get_node_names().get(nid)


def chs_time(dt, future_=u"穿越了", default=u"刚刚"):
    now = datetime.now()
    if now > dt:
        diff = now - dt
        dt_is_past = True
    else:
        diff = dt - now
        dt_is_past = False

    periods = (
        (diff.days / 365, u'年'),
        (diff.days / 30, u'个月'),
        (diff.days / 7, u'星期'),
        (diff.days, u'天'),
        (diff.seconds / 3600, u'小时'),
        (diff.seconds / 60, u'分钟'),
        (diff.seconds, u'秒'),
    )

    if dt_is_past:
        for period, chs_period in periods:
            if period:
                return '%d%s' % (period, chs_period + u'前')
    else:
        return future_
    return default
