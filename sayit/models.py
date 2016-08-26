# coding: utf-8
from datetime import datetime, timedelta
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.dialects.mysql import MEDIUMINT, TINYINT
from flask_login import UserMixin
from exts import bcrypt
from .util.safe_token import create_auth_token
from . import db


def get_or_create(session, model, **kwargs):
    try:
        return session.query(model).filter_by(**kwargs).one(), True
    except NoResultFound:
        new_row = model(**kwargs)
        return new_row, False


def parse_acton(tablename):
    return tablename.replace('user', '').replace('_', '')


def same_id_multiple_asso(model_name, backref_name, foreign_key):
    return db.relationship(model_name,
                           backref=db.backref(backref_name, lazy='dynamic'),
                           uselist=False,
                           foreign_keys=[foreign_key])


def one_to_many(model_name, backref_name):
    return db.relationship(model_name,
                           uselist=False,
                           backref=db.backref(backref_name, lazy='dynamic'))


def join_user_id(cls, id_column):
    column = '{0}.{1}'.format(cls.__tablename__.title(), id_column)
    return db.relationship('User',
                           primaryjoin='User.id=={0}'.format(column),
                           foreign_keys=[User.id],
                           uselist=False)


class IDColumn(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)


class UserRole(db.Model):
    __tablename__ = 'user_role'

    id = db.Column(TINYINT, primary_key=True)
    name = db.Column(db.String(10), nullable=False)
    allow_post = db.Column(TINYINT, nullable=False, server_default='0')
    is_admin = db.Column(TINYINT, nullable=False, server_default='0')

    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def create_role():
        r1 = UserRole(id=1, name=u'创建者', allow_post=1, is_admin=1)
        r2 = UserRole(id=2, name=u'管理员', allow_post=1, is_admin=1)
        r3 = UserRole(id=3, name=u'验证会员', allow_post=1, is_admin=0)
        r4 = UserRole(id=4, name=u'未验证会员', allow_post=0, is_admin=0)
        r5 = UserRole(id=5, name=u'禁言会员', allow_post=0, is_admin=0)

        db.session.add_all([r1, r2, r3, r4, r5])
        db.session.commit()


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id = db.Column(MEDIUMINT, primary_key=True)
    role_id = db.Column(TINYINT, db.ForeignKey('user_role.id'), nullable=False, server_default='4')
    role_expire_day = db.Column(db.Date, nullable=False, server_default='2046-01-01')
    username = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(35), nullable=False)
    email_private = db.Column(TINYINT, nullable=False, server_default='1')
    password_hash = db.Column(db.String(128), nullable=False)
    sign_up_time = db.Column(db.DateTime, nullable=False,  default=datetime.now)
    email_confirmed = db.Column(TINYINT, nullable=False, server_default='0')
    city = db.Column(db.String(50), nullable=False, server_default='0')
    company = db.Column(db.String(50), nullable=False, server_default='0')
    github = db.Column(db.String(50), nullable=False, server_default='0')
    website = db.Column(db.String(50), nullable=False, server_default='0')
    avatar_extension = db.Column(db.String(3), nullable=False, server_default='0')

    @staticmethod
    def generate_fake():
        from sqlalchemy.exc import IntegrityError
        from random import seed, randint
        from faker import Factory
        fake = Factory.create()
        inside_fake = Factory.create('zh_CN')

        start = datetime.now() - timedelta(days=1)
        seed()
        for i in range(50):
            name = fake.user_name()[:8]
            u = User(id=10 + i,
                     username=name,
                     role_id=3,
                     password=name,
                     email='{0}@gmail.com'.format(name),
                     sign_up_time=start + timedelta(minutes=randint(1, 10)),
                     city=inside_fake.city_name(),
                     email_confirmed=1,
                     avatar_extension='png',
                     github=name,
                     website='https://{0}.com'.format(name),
                     email_private=0)
            db.session.add(u)
            try:
                db.session.commit()
            except:
                db.session.rollback()

    def set_ban_post_role(self):
        self.role_id = 5

    def set_verify_role(self):
        self.email_confirmed = 1
        self.role_id = 3

    def set_admin_role(self):
        self.role_id = 1

    @property
    def unread_notice_count(self):
        count = 0
        for row in self.r_notices.all():
            if not row.is_read:
                count += 1
        return count

    def get_post_count(self, attr):
        post = {
            'topic': self.topics,
            'reply': self.replies,
        }
        return post[attr].filter_by(is_delete=0).count()

    def get_not_cancel_count(self, attr):
        attrs = {
            'follow': 'following',
            'follower': 'followed',
            'block': 'blocking',
            'blocker': 'blocked',
        }

        count = 0
        for row in getattr(self, attrs[attr]).all():
            if not row.is_cancel:
                count += 1
        return count

    @property
    def can_post(self):
        can = False
        if self.role.allow_post:
            can = True
        return can

    @property
    def is_admin(self):
        return self.role_id == 2 or self.role_id == 1

    @property
    def is_ban_post(self):
        ban = False
        if u'禁言' in self.role.name:
            ban = True
        return ban

    def get_auth_token(self):
        data = [str(self.id), self.password_hash]
        return create_auth_token(data)

    @property
    def password(self):
        raise AttributeError('you chould not direct read password')

    @password.setter
    def password(self, password_text):
        self.password_hash = bcrypt.generate_password_hash(password_text)

    def password_is_correct(self, password_text):
        return bcrypt.check_password_hash(self.password_hash, password_text)

    def __getattr__(self, name):
        if name not in self.__dict__:
            if '_count' in name:
                short = name.replace('_count', '')
                if short in ['topic', 'reply']:
                    return self.get_post_count(short)
                elif short in ['follow', 'follower', 'block', 'blocker']:
                    return self.get_not_cancel_count(short)

        return db.Model.__getattribute__(self, name)

    def __repr__(self):
        return '<uid #{0}>'.format(self.id)


class TopicReplyBase(IDColumn):
    __abstract__ = True

    @declared_attr
    def user_id(cls):
        return db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False)

    @declared_attr
    def content(cls):
        return db.deferred(db.Column(db.UnicodeText(collation='utf8mb4_unicode_ci'), nullable=False))

    @declared_attr
    def content_html(cls):
        return db.deferred(db.Column(db.UnicodeText(collation='utf8mb4_unicode_ci'), nullable=False))

    @declared_attr
    def delete_by(cls):
        return join_user_id(cls, 'delete_uid')

    delete_uid = db.Column(MEDIUMINT, nullable=False, server_default='0')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)
    is_delete = db.Column(TINYINT, nullable=False, server_default='0')


class Topic(TopicReplyBase):
    __tablename__ = 'topic'

    node_id = db.Column(TINYINT, db.ForeignKey('node.id'))
    title = db.Column(db.UnicodeText(25, collation='utf8mb4_unicode_ci'), nullable=False)
    content_edit_time = db.Column(db.DateTime, nullable=False, server_default='1990-01-01 00:00:00')
    content_edit_uid = db.Column(MEDIUMINT, nullable=False, server_default='0')
    click_count = db.Column(db.Integer, nullable=False, server_default='0')
    is_elite = db.Column(TINYINT, nullable=False, server_default='0')
    elite_edit_uid = db.Column(MEDIUMINT, nullable=False, server_default='0')
    is_pin = db.Column(TINYINT, nullable=False, server_default='0')
    pin_edit_uid = db.Column(MEDIUMINT, nullable=False, server_default='0')
    last_reply_time = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @declared_attr
    def author(cls):
        return same_id_multiple_asso('User', 'topics', cls.user_id)

    @declared_attr
    def elite_editor(cls):
        return join_user_id(cls, 'elite_edit_uid')

    @declared_attr
    def pin_editor(cls):
        return join_user_id(cls, 'pin_edit_uid')

    @declared_attr
    def content_editor(cls):
        return join_user_id(cls, 'content_edit_uid')

    replies = db.relationship('Reply', backref='topic', lazy='dynamic')

    @property
    def reply_count(self):
        return self.replies.count()

    def get_count(self, name):
        count = 0
        for row in getattr(self, name + '_users').all():
            if not row.is_cancel:
                count += 1
        return count

    def reply_ids(self):
        ids = []
        for r in self.replies.all():
            ids.append(r.id)
        return ids

    @staticmethod
    def generate_fake():
        from random import seed, randint
        from faker import Factory
        fake = Factory.create('zh_CN')

        now = datetime.now()
        start = now - timedelta(minutes=1080)
        dt = start + timedelta(minutes=randint(10, 100))
        seed()
        for i in range(79):
            content = fake.paragraphs(nb=3)[0]
            t = Topic(id=100 + i,
                      user_id=randint(10, 59),
                      node_id=randint(101, 105),
                      title=fake.country() + fake.city_name() + fake.street_name(),
                      content=content,
                      create_time=dt,
                      content_html=u'<p>{0}</p>'.format(content),
                      click_count=randint(10, 500),
                      last_reply_time=dt,
                      )
            db.session.add(t)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise

    def __getattribute__(self, name):
        dynamic = [a + '_count' for a in ['upvote', 'bookmark', 'follow']]
        if name in dynamic:
            return self.get_count(name.replace('_count', ''))
        else:
            return TopicReplyBase.__getattribute__(self, name)

    def __repr__(self):
        return '<tid #{0}>'.format(self.id)


class Reply(TopicReplyBase):
    __tablename__ = 'reply'

    @declared_attr
    def author(cls):
        return same_id_multiple_asso('User', 'replies', cls.user_id)

    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False)
    current_floor = db.Column(db.SmallInteger, nullable=False, server_default='0')

    @property
    def upvote_count(self):
        count = 0
        for row in self.upvote_users:
            if not row.is_cancel:
                count += 1
        return count

    # @hybrid_property
    # def upvote_count(self):
    #     return self.upvote_users.count()

    # @upvote_count.expression
    # def upvote_count(cls):
    #     return (select([func.count(UserUpvoteReply.uid)]).
    #             where(UserUpvoteReply.rid == cls.id).
    #             label("upvote_count")
    #             )

    @staticmethod
    def generate_fake(count=886):
        from random import seed, randint
        from faker import Factory
        fake = Factory.create('zh_CN')
        start = datetime.now() - timedelta(days=1)
        seed()
        for i in range(count):
            dt = start + timedelta(minutes=randint(i + 540, i + 550))
            tid = randint(100, 170)
            topic = Topic.query.get(tid)
            floor = topic.reply_count + 1
            content = fake.paragraphs(nb=2)[0]
            r = Reply(user_id=randint(10, 59),
                      topic_id=tid,
                      content=content,
                      content_html=u'<p>{0}</p>'.format(content),
                      current_floor=floor,
                      create_time=dt,
                      )
            topic.last_reply_time = dt
            db.session.add(r)
        try:
            db.session.commit()
        except:
            db.session.rollback()

    def __repr__(self):
        return '<rid #{0}>'.format(self.id)


class CancelableBase(db.Model):
    __abstract__ = True

    is_cancel = db.Column(TINYINT, nullable=False, server_default='0')
    edit_time = db.Column(db.DateTime, nullable=False,  default=datetime.now)


class UserToUserBase(CancelableBase):
    __abstract__ = True

    @declared_attr
    def uid(cls):
        return db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    @declared_attr
    def act_on_uid(cls):
        return db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    @declared_attr
    def come_from(cls):
        """正向 发起的用户 关系为英文动作加ing"""
        action = cls.parse_table_action()
        return same_id_multiple_asso('User', action + 'ing', cls.uid)

    @declared_attr
    def apply_to(cls):
        """反向 施加于用户 关系为英文动作加ed"""
        action = cls.parse_table_action()
        return same_id_multiple_asso('User', action + 'ed', cls.act_on_uid)

    @classmethod
    def parse_table_action(cls):
        """表动作"""
        return cls.__tablename__.replace('user', '').replace('_', '')


class UserFollowUser(UserToUserBase):
    __tablename__ = 'user_follow_user'

    @staticmethod
    def generate_fake():
        from random import seed, randint

        seed()
        for from_uid in range(10, 60):
            added = []
            for i in range(randint(0, 20)):
                to_uid = randint(10, 59)
                if from_uid != to_uid and to_uid not in added:
                    f = UserFollowUser(uid=from_uid,
                                       act_on_uid=to_uid)
                    db.session.add(f)
                    added.append(to_uid)
        try:
            db.session.commit()
        except:
            raise
            db.session.rollback()

    def __repr__(self):
        return '<user follow from:{0} on:{1}>'.format(self.uid, self.act_on_uid)


class UserBlockUser(UserToUserBase):
    __tablename__ = 'user_block_user'

    def __repr__(self):
        return '<user block from:{0} on:{1}>'.format(self.uid, self.act_on_uid)


class UserToTopicBase(CancelableBase):
    __abstract__ = True

    @declared_attr
    def uid(cls):
        return db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False, primary_key=True)

    @declared_attr
    def tid(cls):
        return db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=False, primary_key=True)

    @declared_attr
    def user(cls):
        action = cls.parse_table_action()
        return one_to_many('User', action + '_topics')

    @declared_attr
    def topic(cls):
        action = cls.parse_table_action()
        return one_to_many('Topic', action + '_users')

    @classmethod
    def parse_table_action(cls):
        return cls.__tablename__.replace('user_', '').replace('_topic', '')


class UserFollowTopic(UserToTopicBase):
    __tablename__ = 'user_follow_topic'

    def __repr__(self):
        return '<topic follow u:{0} t:{1}>'.format(self.uid, self.tid)


class UserUpvoteTopic(UserToTopicBase):
    __tablename__ = 'user_upvote_topic'

    def __repr__(self):
        return '<topic upvote u:{0} t:{1}>'.format(self.uid, self.tid)


class UserBookmarkTopic(UserToTopicBase):
    __tablename__ = 'user_bookmark_topic'

    def __repr__(self):
        return '<topic bookmark u:{0} t:{1}>'.format(self.uid, self.tid)


class UserNotice(IDColumn):
    __tablename__ = 'user_notice'

    notice_type = db.Column(db.String(20), nullable=False, server_default='0')
    from_uid = db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False)
    to_uid = db.Column(MEDIUMINT, db.ForeignKey('user.id'), nullable=False)
    notice_releate_id = db.Column(db.Integer, nullable=False, server_default='0')
    reply_id = db.Column(db.Integer, nullable=False, server_default='0')
    is_read = db.Column(db.SmallInteger, nullable=False, server_default='0')
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.now)

    @property
    def topic(self):
        if 'topic' in self.notice_type\
            or 'reply' in self.notice_type\
                or 'mention' in self.notice_type:
            return Topic.query.get(self.notice_releate_id)
        else:
            raise AttributeError('this notice is not about topic')

    @property
    def user(self):
        if 'user' in self.notice_type:
            return User.query.get(self.notice_releate_id)
        else:
            raise AttributeError('this notice is not about user')

    @property
    def reply(self):
        if 'reply' or 'mention' in self.notice_type:
            return Reply.query.get(self.reply_id)
        else:
            raise AttributeError('this notice is not about reply')

    sender = same_id_multiple_asso('User', 's_notices', from_uid)
    receiver = same_id_multiple_asso('User', 'r_notices', to_uid)

    def __repr__(self):
        return '<notice #{0}>'.format(self.id)


class UserAttechment(IDColumn):
    __tablename__ = 'user_attachment'

    uid = db.Column(MEDIUMINT, db.ForeignKey('user.id'))
    file_key = db.Column(db.String(200), nullable=False)
    file_hash = db.Column(db.String(200), nullable=False)
    upload_time = db.Column(db.DateTime, nullable=False, default=datetime.now)

    user = one_to_many('User', 'upload_files')


class UserUpvoteReply(CancelableBase):
    __tablename__ = 'user_upvote_reply'

    uid = db.Column(MEDIUMINT, db.ForeignKey('user.id'), primary_key=True)
    rid = db.Column(db.Integer, db.ForeignKey('reply.id'), primary_key=True)

    user = one_to_many('User', 'upvote_replies')
    reply = one_to_many('Reply', 'upvote_users')

    def __repr__(self):
        return '<reply upvote u:{0} r:{1}>'.format(self.uid, self.rid)


class Node(IDColumn):
    __tablename__ = 'node'

    id = db.Column(TINYINT, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    parent_node = db.Column(TINYINT, nullable=False, server_default='0')
    description = db.Column(db.String(50), nullable=False, server_default='0')

    @property
    def parent(self):
        return Node.query.get(self.parent_node)

    topics = db.relationship('Topic', backref='node', lazy='dynamic')

    @staticmethod
    def create_node():
        f1 = Node(id=1, name=u'父1', parent_node=1)
        f2 = Node(id=2, name=u'父2', parent_node=2)
        f3 = Node(id=3, name=u'父3', parent_node=3)
        db.session.add_all([f1, f2, f3])

        c1 = Node(id=101, name=u'子1', parent_node=1)
        c2 = Node(id=102, name=u'子2', parent_node=2)
        c3 = Node(id=103, name=u'子3', parent_node=3)

        db.session.add_all([c1, c2, c3])
        db.session.commit()

    @staticmethod
    def create_product_node():
        f1 = Node(id=1, name=u'分享', parent_node=1)
        f2 = Node(id=2, name=u'开发', parent_node=2)
        f3 = Node(id=3, name=u'生活', parent_node=3)
        db.session.add_all([f1, f2, f3])

        c1 = Node(id=101, name=u'扯淡', parent_node=1)
        c2 = Node(id=102, name=u'其他', parent_node=1)
        c3 = Node(id=103, name=u'前端', parent_node=2)
        c4 = Node(id=104, name=u'后端', parent_node=2)
        c5 = Node(id=105, name=u'娱乐', parent_node=3)
        db.session.add_all([c1, c2, c3, c4, c5])
        db.session.commit()

    def __repr__(self):
        return '<node #{0}>'.format(self.id)
