import os
from flask import Flask
from app.py_001_embedded_signing.views import bp_001
from app.py_002_email_send_template.views import bp_002
from app.py_004_email_send.views import bp_004
from app.py_005_envelope_list_status.views import bp_005
from app.py_006_envelope_status.views import bp_006
from app.py_007_envelope_recipient_status.views import bp_007
from app.lib_master_python.json_session_interface import JSONSessionInterface

session_path = '/tmp/python_recipe_sessions'

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = ']V<\4/)qC?EwWnd9'
app.register_blueprint(bp_001, url_prefix='/py_001_embedded_signing')
app.register_blueprint(bp_002, url_prefix='/py_002_email_send_template')
app.register_blueprint(bp_004, url_prefix='/py_004_email_send')
app.register_blueprint(bp_005, url_prefix='/py_005_envelope_list_status')
app.register_blueprint(bp_006, url_prefix='/py_006_envelope_status')
app.register_blueprint(bp_007, url_prefix='/py_007_envelope_recipient_status')

if 'DYNO' in os.environ:  # On Heroku?
    import logging
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Recipe example startup')
    app.config.update(dict(PREFERRED_URL_SCHEME = 'https'))

from app import views

if not os.path.exists(session_path):
    os.mkdir(session_path)
    os.chmod(session_path, int('700', 8))
app.session_interface = JSONSessionInterface(session_path)