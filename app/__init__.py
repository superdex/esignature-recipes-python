import os
from flask import Flask
from app.py_010_webhook.views import bp

app = Flask(__name__)
app.register_blueprint(bp, url_prefix='/py_010_webhook')

if os.environ.get('HEROKU') is not None:
    import logging
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Recipe example startup')

from app import views
