import os
from flask import Flask
from app.py_004_email_send.views import bp_004
from app.lib_master_python.json_session_interface import JSONSessionInterface

session_path = '/tmp/python_recipe_sessions'

app = Flask(__name__)
app.secret_key = ']V<\4/)qC?EwWnd9'
app.register_blueprint(bp_004, url_prefix='/py_004_email_send')

if os.environ.get('HEROKU') is not None:
    import logging
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Recipe example startup')

from app import views

if not os.path.exists(session_path):
    os.mkdir(session_path)
    os.chmod(session_path, int('700', 8))
app.session_interface = JSONSessionInterface(session_path)