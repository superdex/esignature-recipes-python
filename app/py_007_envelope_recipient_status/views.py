from flask import render_template, Blueprint, flash, redirect
import py_007_envelope_recipient_status_lib
from app.lib_master_python import ds_recipe_lib

bp_007 = Blueprint('py_007_envelope_recipient_status', __name__)

@bp_007.route('/')  # Sends the envelope and shows the result
def index():
    r = py_007_envelope_recipient_status_lib.start()
    if r["err"]:
        flash(r["err"])
        return redirect("../")
    else:
        return render_template('generic_show_response.html', title='EnvelopeRecipients: list--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar
