# DocuSign API Send Signing Request via Email Recipe 004 (PYTHON)

# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, socket, certifi, requests, os, base64, re, urllib, shutil
# See http://requests.readthedocs.org/ for information on the requests library
# See https://urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_webhook
from flask import  session

# Either set the names/email of the recipients, or fake names will be used
doc_document_path = "app/static/sample_documents_master/NDA.pdf"
doc_document_name = "NDA.pdf"
ds_signer1_email_orig = "***"
ds_signer1_name_orig = "***"
ds_cc1_email_orig = "***"
ds_cc1_name_orig = "***"

def send():
    """Sends the envelope

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
    # STEP 2 - Create and send envelope
    #

    # construct the body of the request
    file_contents = open(doc_document_path, "rb").read()

    # Please use the most accurate and relevant subject line.
    subject = "Please sign the NDA package"
    # File contents are provided here
    # The documents array can include multiple documents, of differing types.
    # All documents are converted to pdf prior to signing.
    # The fileExtension field defaults to "pdf".
    documents = [{"documentId": "1", 
            "name": doc_document_name,
            "fileExtension": os.path.splitext(doc_document_path)[1][1:],
            "documentBase64": base64.b64encode(file_contents)}
        ]
    
    # The signing fields
    #
    # Invisible (white) Anchor field names for the NDA.pdf document:
    #   * signer1sig
    #   * signer1name
    #   * signer1company
    #   * signer1date
    #
    fields = {
    "signHereTabs": [{
        "anchorString": "signer1sig", # Anchored for doc 1
        "anchorXOffset": "0",
        "anchorYOffset": "0",
        "anchorUnits": "mms",
        "recipientId": "1",
        "name": "Please sign here",
        "optional": "false",
        "scaleValue": 1,
        "tabLabel": "signer1sig"}],
    "fullNameTabs": [{
        "anchorString": "signer1name", # Anchored for doc 1
        "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Full Name",
        "name": "Full Name"}],
    "textTabs": [{                 
        "anchorString": "signer1company", # Anchored for doc 1
        "anchorYOffset": "-8",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Company",
        "name": "Company",
        "required": "true"}],
    "dateSignedTabs": [{
        "anchorString": "signer1date", # Anchored for doc 1
        "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "name": "Date Signed",
        "tabLabel": "date_signed"}]
    }
    
    signers = [{"email": ds_signer1_email,
                "name": ds_signer1_name,
                "recipientId": "1",
                "routingOrder": "1",
                "tabs": fields}]
    
    ccs = [{"email": ds_cc1_email,
                "name": ds_cc1_name,
                "recipientId": "2",
                "routingOrder": "2"}]
    
    data = {"emailSubject": subject,
        "documents": documents, 
        "recipients": {"signers": signers, "carbonCopies": ccs},
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
    















