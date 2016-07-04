# DocuSign API Send Signing Request from Template via Email Recipe 002 (PYTHON)

# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, socket, certifi, requests, os, base64, re, urllib, shutil
# See http://requests.readthedocs.org/ for information on the requests library
# See https://urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_webhook
from flask import request, session

# Either set the names/email of the recipients, or fake names will be used
ds_signer1_email_orig = "***"
ds_signer1_name_orig = "***"
ds_cc1_email_orig = "***"
ds_cc1_name_orig = "***"

signer1_role = "signer 1"
cc_role = "cc" # The signer and cc role names must be in agreement with the template's settings

def send():
    """Sends the envelope from a template

    Parameters:
        template_name
        company_name

    Returns r: {
        err: False, or an error message
        html: html output, to be displayed
        envelope_id:
        }
    """

    # Ready...
    # Possibly create some fake people
    ds_signer1_email = ds_recipe_lib.get_signer_email(ds_signer1_email_orig)
    ds_signer1_name = ds_recipe_lib.get_signer_name(ds_signer1_name_orig)
    ds_cc1_email = ds_recipe_lib.get_signer_email(ds_cc1_email_orig)
    ds_cc1_name = ds_recipe_lib.get_signer_name(ds_cc1_name_orig)

    # STEP 1 - Fetch Authentication information from session
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    #
    # STEP 2 - lookup the template
    #
    template_name = request.form.get('template_name')
    company_name = request.form.get('company_name')
    if not template_name:
        return {"err": "Please fill in a template name"}
    if not company_name:
        return {"err": "Please fill in a company name"}

    # Templates: list. See https://docs.docusign.com/esign/restapi/Templates/Templates/list/
    url = auth["base_url"] + "/templates?" + "search_text={}".format(urllib.quote(template_name))
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Templates:list: " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign Templates:list<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    if data["resultSetSize"] == "0":
        return {"err": "No Templates with title {} were found.".format(template_name)}

    # Use the first template_id in the results
    template_id = data["envelopeTemplates"][0]["templateId"]

    # When we create the envelope, we want to set the text tag with the company name value.
    # To set a value, we need the tab's "tabLabel". If it were an agreed value with the person
    # who created the tab, that'd be fine. For the purpose of this example, we'll be more
    # flexible: we'll get the details on the template, and then assume that the first text tab
    # is the company tab. You wouldn't want to do this in production since someone might add
    # an additional text tab to the template, which would break the integration.

    # Use the Templates: get method to retrieve full info about the template.
    # See https://docs.docusign.com/esign/restapi/Templates/Templates/get/
    url = auth["base_url"] + "/templates/{}".format(urllib.quote(template_id))
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Templates:list: " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign Templates:list<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    company_tabLabel = data["recipients"]["signers"][0]["tabs"]["textTabs"][0]["tabLabel"]

    #
    # STEP 2 - Create and send envelope
    #
    # Since we're using a template, this request is relatively small
    # The signer and cc role names must be in agreement with the template's settings
    template_role_signer_1 = {
        "roleName": signer1_role,
        "email": ds_signer1_email,
        "name": ds_signer1_name,
        "tabs": {
            "textTabs": [
                {"tabLabel": company_tabLabel, "value": company_name}
            ]
        }
    }
    template_role_cc = {
        "roleName": cc_role,
        "email": ds_cc1_email,
        "name": ds_cc1_name
    }
    data = {
        "templateId": template_id,
        "templateRoles": [template_role_signer_1, template_role_cc],
        "status": "sent"
    }
    eventNotification = ds_webhook.get_eventNotification_object()
    if eventNotification:
        data["eventNotification"] = eventNotification
        
    # append "/envelopes" to the baseUrl and use in the request
    url = auth["base_url"] + "/envelopes"
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    try:
        r = requests.post(url, headers=ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Envelopes:create: " + str(e)}
        
    status = r.status_code
    if (status != 201): 
        return ({'err': "Error calling DocuSign Envelopes:create<br/>Status is: " +
            str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    envelope_id = data['envelopeId']
    
    # Instructions for reading the email
    webhook_instructions = ds_webhook.webhook_instructions(envelope_id)
    html =  ("<h2>Envelope created, Signature request sent!</h2>" +
            "<p>Envelope ID: " + envelope_id + "</p>" +
            "<p>Signer: " + ds_signer1_name + "</p>" +
            "<p>CC: " + ds_cc1_name + "</p>")
    if webhook_instructions:
        html += (
            "<h2>Next steps:</h2>" +
            webhook_instructions +
            "<h3>2. Sign the envelope</h3>")
    else:
        html += "<h2>Next step:</h2>"

    ds_signer1_email_access = ds_recipe_lib.get_temp_email_access(ds_signer1_email)
    if (ds_signer1_email_access):
        # A temp account was used for the email
        html += "<p>Respond to the request via your mobile phone by using the QR code: </p>" + \
                "<p>" + ds_recipe_lib.get_temp_email_access_qrcode(ds_signer1_email_access) + "</p>" + \
                "<p> or via <a target='_blank' href='" + ds_signer1_email_access + "'>your web browser.</a></p>"
    else:
        # A regular email account was used
        html += "<p>Respond to the request via your mobile phone or other mail tool.</p>" + \
                "<p>The email was sent to " + ds_signer1_name + " &lt;" + ds_signer1_email + "&gt;</p>"

    return {
        "err": False,
        "envelope_id": envelope_id,
        "ds_signer1_email": ds_signer1_email,
        "ds_signer1_name": ds_signer1_name,
        "ds_signer1_access": ds_signer1_email_access,
        "ds_signer1_qr": ds_signer1_email,
        "ds_cc1_email": ds_cc1_email,
        "ds_cc1_name": ds_cc1_name,
        "html": html
    }

########################################################################
########################################################################

# FIN
    















