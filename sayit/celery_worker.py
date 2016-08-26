import os
from . import create_app
from exts import celery


app = create_app(os.getenv('FLKCONF') or 'product')
app.app_context().push()
