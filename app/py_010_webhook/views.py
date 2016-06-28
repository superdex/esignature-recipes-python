from flask import Flask, render_template, flash, redirect, session, url_for, request, g, jsonify, Blueprint
import os.path
import lib
from app.lib_master_python import ds_recipe_lib

bp_010 = Blueprint('py_010_webhook', __name__,
                   template_folder='templates', static_folder='static')
@bp_010.route('/')
def index():
    return render_template('index.html', title='Home - Webhook--Python', base_url=ds_recipe_lib.get_base_url(2))

@bp_010.route('/send')
def sent():
    r = lib.send()
    return render_template('generic_sent.html', title='Sent - Webhook--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
    
@bp_010.route('/webhook', methods=['POST'])
def webhook():
    r = lib.webhook_listener()
    return render_template('webhook.html')

@bp_010.route('/status_page/<envelope_id>') # empty status page
def status_page(envelope_id):
    r = lib.status_page(envelope_id)
    return render_template('status_page.html', title='Notifications - Webhook--Python', data=r, base_url=ds_recipe_lib.get_base_url(3))

@bp_010.route('/status_items/<envelope_id>') # list all status items
def status_items(envelope_id):
    r = lib.status_items(envelope_id)
    return jsonify(items=r)














