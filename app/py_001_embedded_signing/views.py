from flask import render_template, Blueprint, flash, redirect, make_response
import py_001_embedded_signing
from app.lib_master_python import ds_recipe_lib

bp_001 = Blueprint('py_001_embedded_signing', __name__)

@bp_001.route('/')  # Sends the envelope and shows the result
def index():
    r = py_001_embedded_signing.send()
    if r["err"]:
        flash(r["err"])
        return redirect(ds_recipe_lib.get_base_url(2))
    else:
        return render_template('generic_sent.html', title='Embedded Signing--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar

@bp_001.route('/get_view')  # Obtains view url and then redirects to it
def get_view():
    r = py_001_embedded_signing.get_view()
    if r["err"]:
        flash(r["err"])
        return redirect(ds_recipe_lib.get_base_url(2))
    else:
        return redirect(r["redirect_url"])
        # We are redirecting the user to the DocuSign signing ceremony
        # Note that there are multiple options for maintaining state.
        # iFrames are never needed and should never be used since the DocuSign embedded signing experience
        # needs the entire screen, especially for people signing via mobiles and tablets

@bp_001.route('/return_url')  # DocuSign redirects to here after the person finishes signing
def return_url():
    r = py_001_embedded_signing.return_url()
    if r["err"]:
        flash(r["err"])
        return redirect(ds_recipe_lib.get_base_url(2))
    else:
        return render_template('generic_sent.html', title='Embedded Signing--Python', data=r, base_url=ds_recipe_lib.get_base_url(2))
        # base_url is the home page in the nav bar

@bp_001.route('/get_doc')  # DocuSign redirects to here after the person finishes signing
def get_doc():
    r = py_001_embedded_signing.get_doc()
    if r["err"]:
        flash(r["err"])
        return redirect(ds_recipe_lib.get_base_url(2))
    else:
        response = make_response(r["pdf"])
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename={}.pdf'.format(r['filename'])
        return response


