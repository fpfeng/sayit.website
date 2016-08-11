import os
from flask import current_app
from qiniu import put_data
from ..exts import celery, qniu
from ..models import db, User


@celery.task(bind=True, max_retries=5, default_retry_delay=60)
def async_upload(self, filename, data):
    try:
        original_filename = filename
        fake_folder = 'avatar/' + str(filename)
        token = qniu.upload_token(current_app.config['QINIU_BUCKET_NAME'], fake_folder, 3600)
        ret, info = put_data(token, fake_folder, data)
        if 'error' not in ret and info.status_code == 200:
            uid = int(original_filename[:-4])
            user = db.session.query(User).get(uid)
            user.avatar_extension = original_filename[-3:]
            db.session.commit()
    except Exception as exc:
        raise self.retry(exc=exc)


@celery.task()
def async_save(filename, data):
    full_path = os.path.join(current_app.config['AVATAR_FOLDER'], filename)
    with open(full_path, 'wb') as file:
        file.write(data)


def save_then_upload(filename, data):
    async_save.delay(filename, data)
    async_upload.delay(filename, data)
