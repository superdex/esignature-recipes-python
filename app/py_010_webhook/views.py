from flask import Flask, render_template, flash, redirect, session, url_for, request, g, jsonify, Blueprint
import os.path
import lib

bp = Blueprint('py_010_webhook', __name__,
    template_folder='templates', static_folder='static')
@bp.route('/')
@bp.route('/index')
def index():
    return render_template('index.html', title='Home - Webhook--Python')

@bp.route('/sent')
def sent():
    r = py_010_webhook_lib.send()
    return render_template('sent.html', title='Sent - Webhook--Python', data=r)

@bp.route('/webhook', methods=['POST'])
def webhook():
    r = py_010_webhook_lib.webhook_listener()
    return render_template('webhook.html')


