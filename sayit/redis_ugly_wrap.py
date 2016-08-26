# coding: utf-8
import ast
import uuid
from datetime import datetime, timedelta
from collections import defaultdict
from flask import current_app
from .models import User, Reply, Node, Topic
from .util.safe_token import parse_email_address
from . import redis_store as rs
from . import db


def today_hottest():
    key = 'site:hottest'
    if rs.exists(key):
        hottest = ast.literal_eval(rs.get(key))
    else:
        hottest = []
        score = {}
        end = datetime.now()
        start = end - timedelta(days=1)
        topics = Topic.query.filter(Topic.create_time.between(start, end)).all()

        for t in topics:  # copy hacker news ranking
            click = topics_list_cached_count(t, 'click')
            hour_from_post = (end - t.create_time).seconds / 3600
            score[t.id] = (int(click) - 1) / (hour_from_post + 2) ** 1.8
        ranked = sorted(topics, key=lambda x: score[x.id], reverse=True)[:11]

        for t in ranked:
            hottest.append(
                           dict(tid=t.id,
                                title=t.title,
                                uid=t.user_id,
                                name=t.author.username,
                                ext=t.author.avatar_extension))
        rs.set(key, hottest)
        rs.expire(key, current_app.config.get('INDEX_CACHE_SECOND', 900))
    return hottest


def site_stats():
    key = 'site:stats'
    if rs.exists(key):
        stats = rs.hgetall(key)
    else:
        stats = {}
        models = ['user', 'topic', 'reply']
        for m in models:
            count = globals()[m.title()].query.filter().count()
            stats[m] = count
            rs.hset(key, m, count)
        rs.expire(key, current_app.config.get('INDEX_CACHE_SECOND', 900))
    return stats


def incr_post_count(user, _type):
    hkey = hset_page_key('user', user.id)
    if rs.exists(hkey):
        rs.hincrby(hkey, _type, 1)
    key = user_post_count_key(user.id, _type)
    if not rs.exists(key):
        _ = period_post_count(user, _type)
    rs.incr(key)


def user_post_count_key(uid, post_type):
    """
    组合返回用户id加发表类型 key
    """
    assert post_type in ['topic', 'reply']
    return 'user:{0}:period:{1}:count'.format(uid, post_type)


def add_user_post_count(user, _type):
    """
    自增主题或帖子计数
    @param user: user object
    @param _type: 'topic', 'reply'
    """
    if not user.is_admin:  # admin dont count
        key = user_post_count_key(user.id, _type)
        if not rs.exists(key):
            _ = period_post_count(user, _type)
        rs.incr(key)


def period_post_count(user, post_type):
    """
    计算指定时间内主题或帖子的数量
    @param user: user object
    @param post_type: 'topic', 'reply'
    """
    key = user_post_count_key(user.id, post_type)
    now = datetime.now()
    start = now - timedelta(hours=current_app.config['FLOODING_HOUR'])

    if rs.exists(key):
        count = int(rs.get(key))
    else:
        attr = {
            'topic': 'topics',
            'reply': 'replies'
        }
        model = globals()[post_type.title()]
        count = getattr(user, attr[post_type]).filter(
                            model.create_time.between(start, now)).count()
        rs.set(key, count)
    return count


def user_can_post(user, _type):
    """
    用户是否可以发表
    @param user: user object
    @param _type: 'topic', 'reply'
    """
    can = True
    if not user.is_admin:  # unlimit
        count = period_post_count(user, _type)
        if not user.can_post or \
                count >= current_app.config['FLOODING_' + _type.upper()]:
            can = False
    return can


def check_mailto_limit(uid):
    """
    限制未激活用户的邮件发送次数 到时重置
    @param uid: user id
    """
    reach_limit = False
    send_count_key = 'user:{0}:mailto:count'.format(uid)
    count = rs.get(send_count_key)
    if count:
        if int(count) < current_app.config['CONFIRM_MAIL_LIMIT']:
            rs.incr(send_count_key)
        else:
            if rs.ttl(send_count_key) == -1:
                rs.expire(send_count_key, current_app.config['CONFIRM_MAIL_COUNTDOWN'])
            reach_limit = True
    else:
        rs.set(send_count_key, 1)
    return reach_limit


def check_token_valid(token):
    """
    检查token使用与否
    """
    not_use_before, email = True, None
    try:
        email = parse_email_address(token)
        if rs.exists(token):
            not_use_before = False
    except:
        not_use_before = False
    finally:
        return not_use_before, email


def mark_token_used(token):
    """
    重置密码邮件token 24小时内有效 使用后redis计数24小时 用后即焚
    """
    rs.set(token, 1)
    rs.expire(token, 86400)


def get_node_list():
    """
    {
        father:[
                {
                    'name': 'child_one',
                    'nid': 1
                }
            ]
    }
    """
    key = 'cached:nodes'
    nodes = rs.get(key)
    if nodes:
        nodes = ast.literal_eval(nodes)
    else:
        nodes = defaultdict(list)
        child_nodes = db.session.\
            query(Node).\
            filter(Node.parent_node != Node.id).\
            order_by(Node.parent_node).\
            all()
        for n in child_nodes:
            nodes[n.parent.name].append(dict(name=n.name, nid=n.id))
        nodes = dict(nodes)
        rs.set(key, nodes)
    return nodes


def get_child_node_id():
    """
    缓存节点
    """
    key = 'cached:nodes:child'
    ids = rs.get(key)
    if ids:
        ids = ast.literal_eval(ids)
    else:
        ids = []
        children = db.session.\
            query(Node).\
            filter(Node.parent_node != Node.id).\
            order_by(Node.parent_node).\
            all()
        for c in children:
            ids.append(c.id)
        rs.set(key, ids)
    return ids


def get_node_names():
    """
    缓存节点
    """
    key = 'cached:nodes:name'
    names = rs.get(key)
    if names:
        names = ast.literal_eval(names)
    else:
        names = {}
        nodes = db.session.query(Node).filter().all()
        for n in nodes:
            names[n.id] = n.name
        rs.set(key, names)
    return names


def update_topic_cache(tid, reply_time, user, is_reply=True):
    """
    更新最后回复缓存 新主题即是楼主信息
    @param tid: topic id
    @param reply_time: datetime object
    @param user: user object
    @param is_reply: new reply or new post
    """
    if is_reply:
        add_reply_count(tid)
    key = topic_cached_key(tid, 'last')
    info = make_reply_info(user, reply_time)
    rs.set(key, info)


def add_click_count(topic):
    """
    自增点击数
    """
    counter_add(topic.id, 'topic', 'click', 1)
    key = topic_cached_key(topic.id, 'click')
    if rs.exists(key):
        rs.incr(key)
    else:
        _ = topics_list_cached_count(topic, 'click')
        rs.incr(key)
    add_clicked_topic(topic.id)


def add_clicked_topic(tid):
    """
    纪录有新点击主题id
    """
    key = 'cached:clicked:topic'
    rs.sadd(key, tid)


def get_clicked_topic():
    """
    返回新点击主题id
    """
    key = 'cached:clicked:topic'
    string_int_set = rs.smembers(key)
    return map(int, string_int_set)


def make_reply_info(user, time):
    """
    制作最后回复信息
    """
    return {
        'uid': user.id,
        'username': user.username,
        'ext': user.avatar_extension,
        'time': time.strftime('%Y-%m-%d %H:%M:%S')
        }


def get_topic_last_reply_info(tid):
    """
    获取最后回复信息
    """
    key = topic_cached_key(tid, 'last')
    info = rs.get(key)
    if info is not None:
        info = ast.literal_eval(info)
    else:
        r = db.session.query(Reply).filter_by(topic_id=tid).order_by(Reply.id.desc()).first()
        if r:
            info = make_reply_info(r.author,
                                   r.create_time)
        else:
            t = db.session.query(Topic).get(tid)
            info = make_reply_info(t.author,
                                   t.create_time)
        rs.set(key, info)
    return info


def get_all_username_list():
    """
    at.js使用的用户名列表
    """
    key = 'cached:usernames'
    names = rs.get(key)
    if names is None:
        names = []
        for r in db.session.query(User.username).filter_by(email_confirmed=1).all():
            names.append(r[0])
        rs.set(key, names)
        rs.expire(key, 900)  # reload every 15 mins
    else:
        names = ast.literal_eval(names)
    return names


def add_reply_count(tid):
    counter_add(tid, 'topic', 'reply', 1)
    rs.incr(topic_cached_key(tid, 'reply'))


def topics_list_cached_count(topic, attr):
    """
    首页回复点击计数
    @param topic: topic object
    @param attr: 'click' or 'reply'
    """
    key = topic_cached_key(topic.id, attr)
    count = rs.get(key)
    if count is None:
        count = getattr(topic, attr + '_count')
        rs.set(key, count)
    return count


def topic_click_count(tid):
    return rs.get(topic_cached_key(tid, 'click'))


def topic_cached_key(tid, attr):
    return 'cached:topic:{0}:{1}'.format(tid, attr)


def get_topic_field_count(tid, field):
    """
    主题计数
    @param: field: 'bookmark', 'follow' etc..
    """
    return rs.hget(hset_page_key('topic', tid), field)


def get_user_page_info(page_user, current_user):
    """
    用户页信息 url用户计数 已登录用户的收藏屏蔽用户uid
    @param page_user: url中的用户
    @param current_user: 当前用户
    """
    asso_ids = None
    if current_user.is_authenticated:
        asso_ids = get_user_asso_ids(current_user, 'user')
    counts = get_page_counter(page_user, 'user')
    return asso_ids, counts


def get_asso_ids(user, key):
    """
    主题或用户的关联id 赞收藏屏蔽等等 对应主题或用户id
    烂实现
    """
    relationship = {
        'topic:upvote': 'upvote_topics',
        'topic:bookmark': 'bookmark_topics',
        'topic:follow': 'follow_topics',
        'reply:upvote': 'upvote_replies',
        'user:following': 'following',
        'user:follower': 'followed',
        'user:block': 'blocking',
    }

    attr = {
        'topic:upvote': 'tid',
        'topic:bookmark': 'tid',
        'topic:follow': 'tid',
        'reply:upvote': 'rid',
        'user:following': 'act_on_uid',
        'user:follower': 'uid',
        'user:block': 'act_on_uid',
    }

    for row in getattr(user, relationship[key]).all():
        if row.is_cancel == 0:
            yield getattr(row, attr[key])


def user_notice_key(uid):
    return 'user:{0}:unread:notice'.format(uid)


def reset_notice_count(uid):
    rs.set(user_notice_key(uid), 0)


def incr_unread_count(uid):
    key = user_notice_key(uid)
    rs.incr(key)


def user_unread_notice_count(user):
    """
    右上角未读信息
    """
    key = user_notice_key(user.id)
    count = rs.get(key)
    if count is None:
        count = user.unread_notice_count
        rs.set(key, count)
    return count


def reply_upvote_count(reply):
    count = rs.get('reply:{0}:upvote'.format(reply.id))
    if count is None:
        count = reply.upvote_count
        rs.set('reply:{0}:upvote'.format(reply.id), count)
        count = str(count)
    return count


def hset_page_key(which_page, xid):
    key = {
        'topic': 'topic:{0}:counts',
        'user': 'user:{0}:counts',
        }
    return key[which_page].format(xid)


def page_counter_attrs(which_page):
    """
    单主题页或查看用户页计数属性
    """
    attrs = {
        'topic': ['reply', 'upvote', 'bookmark', 'follow', 'click'],
        'user': ['reply', 'topic', 'follow', 'follower', 'block', 'blocker']
    }
    return attrs[which_page]


def get_page_counter(obj, which_page):
    """
    单主题页或查看用户页计数集合
    """
    hset_key = hset_page_key(which_page, obj.id)
    if not rs.exists(hset_key):
        counters = {}
        p = rs.pipeline()
        for attr in page_counter_attrs(which_page):
            v = getattr(obj, attr + '_count')
            counters[attr] = str(v)
            p.hset(hset_key, attr, v)
        p.execute()
    else:
        counters = rs.hgetall(hset_key)
    return counters


def hset_topic_key(tid):
    return 'topic:{0}:counts'.format(tid)


def xid_cached_key(which_page):
    keys = {
        'topic': 'cached:user:topic',
        'user': 'cached:user:user',
        'reply': 'cached:topic:reply',
    }
    return keys[which_page]


def page_releate_id_cached(xid, which_page):
    return rs.sismember(xid_cached_key(which_page), xid)


def mark_page_releate_id_cached(xid, which_page):
    rs.sadd(xid_cached_key(which_page), xid)


def uid_key_head(uid):
    return 'user:{0}:'.format(uid)


def single_asso_key(uid, table, action):
    assert table in ['reply', 'topic', 'user'] \
        and action in ['upvote', 'bookmark', 'follow', 'block']

    head = uid_key_head(uid)
    table += ':'

    if table == 'user' and action == 'follow':
        action += 'ing'

    return head + table + action


def user_asso_key(uid, which_page):
    head = uid_key_head(uid)
    keys = {
            'topic': [
                        'topic:upvote',
                        'topic:bookmark',
                        'topic:follow',
                        'reply:upvote',
                        'user:block'
                    ],
            'user': [
                        'user:following',
                        'user:follower',
                        'user:block',
            ],
        }
    key = keys[which_page]
    return [head + k for k in key], key  # redis, view


def get_user_asso_ids(user, which_page):
    """
    返回用户相对页面的关联id集合
    """
    all_ids = {}
    for_redis, for_view_render = user_asso_key(user.id, which_page)

    if page_releate_id_cached(user.id, which_page):
        for index, k in enumerate(for_redis):
            string_int_set = rs.smembers(k)
            all_ids[for_view_render[index]] = map(int, string_int_set)
    else:
        p = rs.pipeline()
        for index, k in enumerate(for_redis):
            row_ids = pipe_add_asso_id(p, user, k, for_view_render[index])
            all_ids[for_view_render[index]] = row_ids
        p.execute()
        mark_page_releate_id_cached(user.id, which_page)

    return all_ids


def pipe_add_asso_id(pipe, user, redis_key, db_attr):
    ids = []
    for _id in get_asso_ids(user, db_attr):
        ids.append(int(_id))
        pipe.sadd(redis_key, _id)
    return ids


def id_is_exist(_id, _type):
    exist = False
    if _type == 'reply':
        exist = rs.exists('reply:{0}:upvote'.format(_id))
    elif _type == 'topic':
        exist = rs.exists(hset_page_key(_type, _id))
    elif _type == 'user':
        exist = True
    return exist


def is_in_set(_id, key):
    return rs.sismember(key, _id)


def oppsite_user_switch(from_uid, following_uid):
    """
    从被关注用户中增减关注用户id
    """
    key = 'user:{0}:user:follower'.format(following_uid)
    if rs.sismember(key, from_uid):
        rs.srem(key, from_uid)
    else:
        rs.sadd(key, from_uid)


def counter_switch(_id, _type, action, key, uid=0):
    if is_in_set(_id, key):
        rs.srem(key, _id)
        current_counter_number = counter_add(_id, _type, action, -1, uid)
        cancel = 1
    else:
        rs.sadd(key, _id)
        current_counter_number = counter_add(_id, _type, action, 1, uid)
        cancel = 0
    return dict(cancel=cancel, current=current_counter_number)


def counter_add(_id, _type, action, number, uid=0):
    if _type == 'reply':
        current = rs.incrby('reply:{0}:upvote'.format(_id), number)
    else:
        if _type == 'user':
            action += 'er'  # key for action on user side
            # remove cache
            # keys1, _ = user_asso_key(_id, 'user')
            # keys2, _ = user_asso_key(uid, 'user')
            # p = rs.pipeline()
            # for index, k in enumerate(keys1):
            #     p.delete(k, keys2[index])
            # p.execute()
            # _ = get_user_asso_ids()
        # only update when counter already pipeline created,
        # otherwise it would break exist check in pipeline func
        if rs.exists(hset_page_key(_type, _id)):
            current = rs.hincrby(hset_page_key(_type, _id), action, number)
        else:
            current = 1
        # add follow from user count
        if action == 'follower':
            if rs.exists(hset_page_key(_type, uid)):
                rs.hincrby(hset_page_key(_type, uid), 'follow', number)
    return current


def generate_qiniu_key():
    key = uuid.uuid4().hex
    rs.set(key, 1)
    rs.expire(key, 600)
    return key


def valid_qiniu_key(key):
    return rs.exists(key)
