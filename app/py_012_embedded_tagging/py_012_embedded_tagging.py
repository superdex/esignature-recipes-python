# DocuSign API Embedded Tagging Recipe 012 (PYTHON)

# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import requests, os, base64, time, urllib, re
# See http://requests.readthedocs.org/ for information on the requests library
# See https://urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_webhook
from flask import request, session

# Either set the names/email of the recipients, or fake names will be used
doc_document_path = "app/static/sample_documents_master/NDA.pdf"
doc_document_name = "NDA.pdf"
sign_button_text = "Sign the NDA agreement!"
ds_signer1_email_orig = "***"  # If you don't have the email for an embedded signer
                               # then create a fake email that includes their clientUserId
ds_signer1_name_orig = "***"
ds_signer1_clientUserId = 1001 # UNIQUELY identifies the signer within your embedded system
ds_cc1_email_orig = "***"
ds_cc1_name_orig = "***"
embedded_tagging_key = "embedded_tagging_key" # Used to store/retrieve the embedded signing details
return_uri = "/py_012_embedded_tagging/return_url" # where DocuSign should redirect to after the person has finished signing
trace_value = "py_012_embedded_tagging" # Used for tracing API calls
trace_key = "X-ray"

def send():
    """Creates the envelope as a draft

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
    # STEP 2 - Create the draft envelope
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
        "name": "Full Name"}]
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
    
    data = {
        "emailSubject": subject,
        "documents": documents, 
        "recipients": {"signers": signers, "carbonCopies": ccs},
        "status": "created"  ### "created" status means we'll get a draft envelope
    }

    eventNotification = ds_webhook.get_eventNotification_object()
    if eventNotification:
        data["eventNotification"] = eventNotification

    # append "/envelopes" to the baseUrl and use in the request
    url = auth["base_url"] + "/envelopes"
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"],
                  trace_key: trace_value}

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
    session['latest_envelope_id'] = envelope_id # Save for other recipe's use

    # Save the information that we will need for the embedded tagging
    # in our "database" (for this example, we're using the session)
    session[embedded_tagging_key] = {
        "envelopeId": envelope_id}

    # Instructions for tagging and sending the envelope
    html =  ("<h2>A draft envelope was created, ready to be tagged and sent!</h2>" +
            "<p>Envelope ID: " + envelope_id + "</p>" +
            "<p>Signer: " + ds_signer1_name + "</p>" +
            "<p>CC: " + ds_cc1_name + "</p>")
    html += (
            "<h2>Next step:</h2>" +

            "<form action='get_view'>" +
            "<p><select name='send'>" +
            "<option value='0'>Start with the prepare page</option>" +
            "<option value='1' selected='selected'>Start with the tagging page</option>" +
            "</select></p>" +
            "<button type='submit' class='btn btn-primary'>Tag and Send the envelope</button>" +
            "</form>")

    return {
        "err": False,
        "envelope_id": envelope_id,
        "ds_signer1_email": ds_signer1_email,
        "ds_signer1_name": ds_signer1_name,
        "ds_signer1_qr": ds_signer1_email,
        "ds_cc1_email": ds_cc1_email,
        "ds_cc1_name": ds_cc1_name,
        "html": html
    }

########################################################################
########################################################################

def get_view():
    """Obtains a sending view from DocuSign. The user will then be redirected to the view url

    Uses the information stored in the session to request the view.
    Query parameter: send = 0 or 1. See https://goo.gl/aLNjJH
    RETURNS {err, redirect_url}
    """    

    err = False # No problems so far!
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    if not embedded_tagging_key in session:
        return {"err": "Embedded signing information missing from session! Please re-send."}

    embedding_info = session[embedded_tagging_key]
    # Obtain the "sender's view" 
    # See https://docs.docusign.com/esign/restapi/Envelopes/EnvelopeViews/createSender/

    return_url = ds_recipe_lib.get_base_url(2) + return_uri
    data = {"returnUrl": return_url}

    # append "/envelopes/{envelopeId}/views/sender" to the baseUrl and use in the request
    url = auth["base_url"] + '/envelopes/{}/views/sender'.format(
        embedding_info["envelopeId"])
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"],
                  trace_key: trace_value}

    try:
        r = requests.post(url, headers=ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling EnvelopeViews:createSender: " + str(e)}

    status = r.status_code
    if (status != 201):
        return ({'err': "Error calling DocuSign EnvelopeViews:createSender<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    redirect_url = data['url']
    # Update the send parameter in the url
    # An example url:
    # https://demo.docusign.net/Member/StartInSession.aspx?StartConsole=1&t=2fABCXYZ6197&DocuEnvelope=2dABCXYZ&send=1
    # We search for send=0|1 and replace it per our incoming "send" parameter
    send_re = re.compile("(\&send=[01])")
    redirect_url = send_re.sub("&send={}".format(request.args.get('send')), redirect_url)
    return {"err": err, "redirect_url": redirect_url}

########################################################################
########################################################################

def return_url():
    """DocuSign redirects to here after the person has finished their sending experience

    Query Parameters "envelopeId" and "event" are supplied by DocuSign
    RETURNS {err, html}
    """

    err = False # No problems so far!

    # Retrieving our "state" about which embedded sending experience has
    # been completed: there are multiple options. iFrames are never needed
    # and should never be used since the DocuSign embedded sending experience
    # needs the entire screen, especially for people sending via mobiles and tablets
    #
    # Options for maintaining state:
    # 1 - Use the session, as we're doing in this example
    # 2 - add your own state query param to your return_url and the additional
    #     query param will be included when DocuSign redirects to your app
    # 3 - DocuSign returns the envelopeId that you want tagged and sent. The
    #     envelopeId can be used to look up state within your app

    status = request.args.get("event")
    # See https://docs.docusign.com/esign/restapi/Envelopes/EnvelopeViews/createRecipient/
    translate_event = {
        "Send": "the user sent the envelope",
        "Save": "the user saved the envelope--it is still in draft mode",
        "Cancel": "the user canceled the sending transaction",
        "Error": "there was an error when sending the envelope",
        "SessionEnd": "the sending session ended before the user sent, saved, or canceled the envelope"}

    # Retrieve state via the session
    if not embedded_tagging_key in session:
        return {"err": "Embedded signing information missing from session!"}
    embedding_info = session[embedded_tagging_key]

    if status != "Send":
        html = ("<h2>The envelope was not sent!</h2>" +
                "<p>Envelope ID: " + embedding_info["envelopeId"] + "</p>" +
                "<p>Tagging/sending outcome: " + translate_event[status] + " [{}]".format(status) + "</p>")
        return {
            "err": err,
            "status": status,
            "html": html
        }

    # Sending is complete!
    html = ("<h2>Envelope was sent!</h2>" +
            "<p>Envelope ID: " + embedding_info["envelopeId"] + "</p>" +
            "<p>Tagging/sending outcome: " + translate_event[status] + " [{}]".format(status) + "</p>" +
            "<p>You can examine the envelope via the DocuSign web browser app.</p>")

    return {
        "err": err,
        "status": status,
        "html": html
    }

# FIN
    















