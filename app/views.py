from flask import Flask, render_template, flash, redirect, session, url_for, request, g, jsonify
from app import app
import os.path
from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_authentication

@app.route('/')
@app.route('/index')
def index():
    return render_template('home.html', title='Home - Python Recipes', base_url=ds_recipe_lib.get_base_url(0))

################################################################################
################################################################################

# Authentication
@app.route('/auth', methods=['GET'])
def get_auth_status():
    return jsonify(ds_authentication.get_auth_status())

@app.route('/auth', methods=['POST'])
def set_auth():
    return jsonify(ds_authentication.set_auth())

@app.route('/auth', methods=['DELETE'])
def delete_auth():
    return jsonify(ds_authentication.delete_auth())



################################################################################
################################################################################

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

