from flask import render_template, Blueprint, flash, redirect
import py_006_envelope_status_lib
from app.lib_master_python import ds_recipe_lib

bp_006 = Blueprint('py_006_envelope_status', __name__)

@bp_006.route('/')  # Sends the envelope and shows the result
def index():
    r = py_006_envelope_status_lib.start()
    if r["err"]:
        flash(r["err"])
        return redirect(ds_recipe_lib.get_base_url(2))
    else:
        return render_template('generic_show_response.html', title='Envelopes: get--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar
