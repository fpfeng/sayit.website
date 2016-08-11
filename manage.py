# coding: utf-8
import os
from flask_script import Manager, Shell
from sayit import create_app, get_models, mail, redis_store, db


def make_shell_context():

    ctx = dict(app=app,
               db=db,
               mail=mail,
               redis_store=redis_store)

    models = get_models()
    combine = ctx.copy()
    combine.update(models)
    return combine

app = create_app(os.getenv('FLKCONF') or 'dev')

manager = Manager(app)

manager.add_command('shell', Shell(make_context=make_shell_context))


@manager.command
def test():
    os.environ['FLKCONF'] = 'test'
    import unittest
    test = unittest.TestLoader().discover('test')
    unittest.TextTestRunner(verbosity=2).run(test)


@manager.command
def cover():
    import coverage
    import unittest
    os.environ['FLKCONF'] = 'test'
    cov = coverage.coverage(
        branch=True,
        include='sayit/*'
    )
    cov.start()
    tests = unittest.TestLoader().discover('test')
    unittest.TextTestRunner(verbosity=2).run(tests)
    cov.stop()
    cov.save()
    print 'Coverage Summary:'
    cov.report()
    basedir = os.path.abspath(os.path.dirname(__file__))
    covdir = os.path.join(basedir, 'coverage')
    cov.html_report(directory=covdir)
    cov.erase()


@manager.command
def fake_site():
    from datetime import datetime, timedelta
    from sayit.models import User, UserRole, Topic, Reply, UserFollowUser, Node
    os.environ['FLKCONF'] = 'dev'
    print 'just wait a moment, ingore truncated username warning'
    ctx = app.app_context()
    ctx.push()
    db.drop_all()
    redis_store.flushdb()
    db.create_all()
    UserRole.create_role()
    Node.create_product_node()
    User.generate_fake()
    Topic.generate_fake()
    Reply.generate_fake()
    UserFollowUser.generate_fake()

    days_ago = datetime.now() - timedelta(days=2)
    a = User(id=1,
             username='admin',
             role_id=1,
             password='adminpwd',
             email='admin@sayit.website',
             avatar_extension='png',
             email_confirmed=1,
             email_private=0,
             github='fpfeng',)
    db.session.add(a)
    db.session.flush()
    p = Topic(id=1,
              user_id=1,
              node_id=101,
              title=u'🙂全站普通用户，名字即是密码，长度6以上可以登录',
              content=u'wtform检测逻辑，密码必须长度6以上。admin密码`adminpwd`。',
              content_html=u'<p>wtform检测逻辑，密码必须长度6以上，看着来吧。admin密码<code>adminpwd</code> 。<p>',
              click_count=101,
              is_pin=1,
              pin_edit_uid=1,
              create_time=days_ago,
              last_reply_time=days_ago,
              is_elite=1,
              elite_edit_uid=1)
    m = Topic(id=2,
              user_id=1,
              node_id=101,
              title=u'代码高亮 楼层爆破 举个🌰',
              content=u'''```def foo():\n    print 'hello world'\n```''',
              content_html=u'''<pre><code>def func():\n    print 'hello world'\n</code></pre>''',
              click_count=101,
              is_elite=1,
              elite_edit_uid=1,
              create_time=days_ago,
              last_reply_time=days_ago,)
    db.session.add_all([p, m])
    db.session.flush()
    for i in range(1, 8):
        r = Reply(user_id=1,
                  topic_id=2,
                  content=u'只拆双数',
                  content_html=u'<p>只拆双数</p>',
                  current_floor=i,
                  delete_uid=1,
                  is_delete=not(bool(i % 2)),
                  create_time=days_ago + timedelta(minutes=i),
                  )
        db.session.add(r)
    db.session.commit()
    ctx.pop()
    print 'done!'


if __name__ == '__main__':
    manager.run()
