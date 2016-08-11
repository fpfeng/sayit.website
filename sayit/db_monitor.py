from models import Reply, UserUpvoteReply, UserToTopicBase, UserFollowUser, Topic
from util.async_task import new_reply, upvote_reply, user_to_topic, user_to_user, \
                new_topic


def is_insert(operate):
    return operate == 'insert'


def is_model(target, model):
    return isinstance(target, model)


def del_user_string(target):
    return target.__tablename__.replace('user_', '')


def receive_change(app, changes):
    for target, operate in changes:
        if is_insert(operate):
            if is_model(target, Reply):
                new_reply.delay(target.user_id,
                                target.topic.user_id,
                                target.topic.id,
                                target.id)
            elif is_model(target, UserUpvoteReply):
                upvote_reply.delay(target.uid, target.rid)
            elif is_model(target, UserToTopicBase):
                action = del_user_string(target)
                user_to_topic.delay(action, target.uid, target.tid)
            elif is_model(target, UserFollowUser):
                action = del_user_string(target)
                user_to_user.delay(action, target.uid, target.act_on_uid)
            elif is_model(target, Topic):
                new_topic.delay(target.user_id, target.id)
