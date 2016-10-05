from flask import Blueprint, render_template, flash, redirect, jsonify, request, session
import py_014_local_search
from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_authentication

bp_014 = Blueprint('py_014_local_search', __name__)

@bp_014.route('/')  # Show screen
def index():
    return render_template('search_page.html', title='Envelope Search', base_url=ds_recipe_lib.get_base_url(2))

@bp_014.route('/db', methods=['GET'])  # Returns current search database
def get_db():
    r = py_014_local_search.get_db()
    redirect_url = ds_authentication.reauthenticate_check(r, ds_recipe_lib.get_base_url(2) + "/py_014_local_search")
    if redirect_url:
        r["err"] = "Please authenticate"
        r["err_code"] = "PLEASE_REAUTHENTICATE"
        r["redirect_url"] = redirect_url
    return jsonify(r)

@bp_014.route('/db', methods=['DELETE'])  # Deletes the cached search database
def delete_db():
    r = py_014_local_search.delete_db()
    redirect_url = ds_authentication.reauthenticate_check(r, ds_recipe_lib.get_base_url(2) + "/py_014_local_search")
    if redirect_url:
        r["err"] = "Please authenticate"
        r["err_code"] = "PLEASE_REAUTHENTICATE"
        r["redirect_url"] = redirect_url
    return jsonify(r)

@bp_014.route('/update_envelope_list', methods=['POST']) # Updates the envelopes list
def update_envelope_list():
    r = py_014_local_search.update_envelope_list()
    redirect_url = ds_authentication.reauthenticate_check(r, ds_recipe_lib.get_base_url(2) + "/py_014_local_search")
    if redirect_url:
        r["err"] = "Please authenticate"
        r["err_code"] = "PLEASE_REAUTHENTICATE"
        r["redirect_url"] = redirect_url
    return jsonify(r)

@bp_014.route('/update_envelopes_list', methods=['POST'])  # Updates the db for one or more envelopes
def update_envelopes_list():
    r = py_014_local_search.update_envelopes_list()
    redirect_url = ds_authentication.reauthenticate_check(r, ds_recipe_lib.get_base_url(2) + "/py_014_local_search")
    if redirect_url:
        r["err"] = "Please authenticate"
        r["err_code"] = "PLEASE_REAUTHENTICATE"
        r["redirect_url"] = redirect_url
    return jsonify(r)





