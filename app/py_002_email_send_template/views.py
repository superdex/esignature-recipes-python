from flask import render_template, Blueprint, flash, redirect, url_for
import py_002_email_send_template_lib
from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_authentication

bp_002 = Blueprint('py_002_email_send_template', __name__, template_folder="templates")

@bp_002.route('/')  # Asks for the template name and company name value
def index():
    return render_template('py_002_form_1.html', title='Template name--Python', base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar

@bp_002.route('/send', methods=['POST'])  # Sends the envelope and shows the result
def send():
    r = py_002_email_send_template_lib.send()
    redirect_url = ds_authentication.reauthenticate_check(r, ds_recipe_lib.get_base_url())
    if redirect_url:
        return redirect(redirect_url)
    if r["err"]:
        flash(r["err"])
        return redirect(url_for('.index')) # Note: redirect to this recipe's index page/form if there's a problem
    else:
        return render_template('generic_sent.html', title='Send Template--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar

