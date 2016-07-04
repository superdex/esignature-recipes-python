# DocuSign API Embedded Signing Recipe 001 (PYTHON)

# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import requests, os, base64, time, urllib
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
embedded_signing_key = "embedded_signing_key" # Used to store/retrieve the embedded signing details
return_uri = "/py_001_embedded_signing/return_url" # where DocuSign should redirect to after the person has finished signing


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
                "clientUserId": ds_signer1_clientUserId, # this signer is an embedded signer
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

    # Save the information that we will need for the embedded signing
    # in our "database" (for this example, we're using the session)
    session[embedded_signing_key] = {
        "email": ds_signer1_email,
        "name": ds_signer1_name,
        "clientUserId": ds_signer1_clientUserId,
        "envelopeId": envelope_id}

    # Instructions for signing the email
    webhook_instructions = ds_webhook.webhook_instructions(envelope_id)
    html =  ("<h2>Envelope created, ready to be signed!</h2>" +
            "<p>Envelope ID: " + envelope_id + "</p>" +
            "<p>Signer: " + ds_signer1_name + "</p>" +
            "<p>CC: " + ds_cc1_name + "</p>")
    if webhook_instructions:
        html += (
            "<h2>Next steps:</h2>" +
            webhook_instructions +
            "<h3>2. Sign the envelope</h3>" +
            "<form action='get_view'>" +
            "<button type='submit' class='btn btn-primary'>" + sign_button_text + "</button>" +
            "</form>")
    else:
        html += (
            "<h2>Next step:</h2>" +

            "<form action='get_view'>" +
            "<button type='submit' class='btn btn-primary'>" + sign_button_text + "</button>" +
            "</form>")

    return {
        "err": False,
        "envelope_id": envelope_id,
        "ds_signer1_email": ds_signer1_email,
        "ds_signer1_name": ds_signer1_name,
        "ds_signer1_clientUserId": ds_signer1_clientUserId,
        "ds_signer1_qr": ds_signer1_email,
        "ds_cc1_email": ds_cc1_email,
        "ds_cc1_name": ds_cc1_name,
        "html": html
    }

########################################################################
########################################################################

def get_view():
    """Obtains a view from DocuSign. The user will then be redirected to the view url

    Uses the information stored in the session to request the view.
    RETURNS {err, redirect_url}
    """

    err = False # No problems so far!
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    if not embedded_signing_key in session:
        return {"err": "Embedded signing information missing from session! Please re-send."}

    embedding_info = session[embedded_signing_key]
    # Obtain the "recipient's view" (In this case, its the signer's view)
    # See https://docs.docusign.com/esign/restapi/Envelopes/EnvelopeViews/createRecipient/

    return_url = ds_recipe_lib.get_base_url(2) + return_uri
    data = {"authenticationMethod": "Password", # How was this recipient authenticated. Pick from list of values
            "clientUserId": embedding_info["clientUserId"],
            "email": embedding_info["email"],
            "userName": embedding_info["name"],
            "returnUrl": return_url
            }

    # append "/envelopes/{envelopeId}/views/recipient" to the baseUrl and use in the request
    url = auth["base_url"] + '/envelopes/{}/views/recipient'.format(embedding_info["envelopeId"])
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}

    try:
        r = requests.post(url, headers=ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling EnvelopeViews:createRecipient: " + str(e)}

    status = r.status_code
    if (status != 201):
        return ({'err': "Error calling DocuSign EnvelopeViews:createRecipient<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    redirect_url = data['url']
    return {"err": err, "redirect_url": redirect_url}

########################################################################
########################################################################

def return_url():
    """DocuSign redirects to here after the person has finished signing

    Query Parameter "event" is supplied by DocuSign
    RETURNS {err, html}
    """

    err = False # No problems so far!

    # Retrieving our "state" about which embedded signing experience has
    # been completed: there are multiple options. iFrames are never needed
    # and should never be used since the DocuSign embedded signing experience
    # needs the entire screen, especially for people signing via mobiles and tablets
    #
    # Options for maintaining state:
    # 1 - Use the session, as we're doing in this example
    # 2 - add your own state query param to your return_url and the additional
    #     query param will be included when DocuSign redirects to your app

    status = request.args.get("event")
    # See https://docs.docusign.com/esign/restapi/Envelopes/EnvelopeViews/createRecipient/
    translate_event = {
        "cancel": "recipient canceled the signing operation",
        "decline": "recipient declined to sign",
        "exception": "an exception occurred",
        "fax_pending": "recipient has a fax pending",
        "session_timeout": "session timed out",
        "signing_complete": "signer completed the signing ceremony",
        "ttl_expired": "the TTL, time to live, timer expired",
        "viewing_complete": "recipient completed viewing the envelope"
    }

    # Retrieve state via the session
    if not embedded_signing_key in session:
        return {"err": "Embedded signing information missing from session!"}
    embedding_info = session[embedded_signing_key]

    if status != "signing_complete":
        html = ("<h2>Envelope was not signed!</h2>" +
                "<p>Envelope ID: " + embedding_info["envelope_id"] + "</p>" +
                "<p>Signing ceremony outcome: " + translate_event[status] + " [{}]".format(status) + "</p>")
        return {
            "err": err,
            "status": status,
            "html": html
        }

    # Signing is complete!
    html = ("<h2>Envelope was signed!</h2>" +
            "<p>Envelope ID: " + embedding_info["envelopeId"] + "</p>" +
            "<p>Signing ceremony outcome: " + translate_event[status] + " [{}]".format(status) + "</p>")

    # Get envelope status from DocuSign if it is available
    envelope_status = get_status(embedding_info["envelopeId"])
    # In the following, the default filename would be better if it included information connecting it
    # to the specific transaction. Eg, for an NDA transaction, it could be the company name and date.
    if envelope_status:
        html += ('<div class="margintop">' +
            "<p>View the envelope's documents and Certificate of Completion</p>" +
            "<p><form class='margintop' action='get_doc'>" +
                '<input type="hidden" name="url" value="{}" />'.format(urllib.quote(envelope_status["certificateUri"])) +
                '<input type="hidden" name="fn" value="{}" />'.format(urllib.quote("Certificate of Completion")) +
                "<button type='submit' class='btn btn-primary'>" + "Certificate of Completion" + "</button>" +
            "</form>" +
            "<form class='margintop' action='get_doc'>" +
                '<input type="hidden" name="url" value="{}" />'.format(urllib.quote(envelope_status["documentsCombinedUri"])) +
                '<input type="hidden" name="fn" value="{}" />'.format(urllib.quote("Combined Documents")) +
                "<button type='submit' class='btn btn-primary'>" + "Combined Documents" + "</button>" +
            "</form>" +
            "</p></div>")

    return {
        "err": err,
        "status": status,
        "html": html
    }

def get_status(envelope_id):
    """Fetch the envelope status from DocuSign

    See https://docs.docusign.com/esign/restapi/Envelopes/Envelopes/get/
    Returns {false or the result of the call}
    """

    # Sample data returned from the Envelopes: Get method
    # {
    #     "status": "completed",
    #     "documentsUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/documents",
    #     "recipientsUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/recipients",
    #     "envelopeUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d",
    #     "emailSubject": "Please sign the NDA package",
    #     "envelopeId": "ed400d38-7765-4ce5-9f50-8652a8c4486d",
    #     "customFieldsUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/custom_fields",
    #     "autoNavigation": "true",
    #     "envelopeIdStamping": "true",
    #     "notificationUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/notification",
    #     "enableWetSign": "true",
    #     "allowMarkup": "false",
    #     "createdDateTime": "2016-06-28T15:57:07.1800000Z",
    #     "lastModifiedDateTime": "2016-06-28T15:57:07.1800000Z",
    #     "deliveredDateTime": "2016-06-28T15:57:33.6270000Z",
    #     "initialSentDateTime": "2016-06-28T15:57:07.7430000Z",
    #     "sentDateTime": "2016-06-28T15:57:33.6270000Z",
    #     "completedDateTime": "2016-06-28T15:57:33.6270000Z",
    #     "statusChangedDateTime": "2016-06-28T15:57:33.6270000Z",
    #     "documentsCombinedUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/documents/combined",
    #     "certificateUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/documents/certificate",
    #     "templatesUri": "/envelopes/ed400d38-7765-4ce5-9f50-8652a8c4486d/templates",
    #     "brandId": "3774f432-9d31-40e6-bc6b-6ae30cce334c",
    #     "purgeState": "unpurged",
    #     "is21CFRPart11": "false",
    #     "isSignatureProviderEnvelope": "false"
    # }

    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return False
    else:
        return False

    # append "/envelopes/{envelopeId}" to the baseUrl and use in the request
    url = auth["base_url"] + '/envelopes/{}'.format(envelope_id) + "?cache_buster={}".format(time.time())
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}

    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return False

    status = r.status_code
    if (status != 200):
        return False

    return r.json()


def get_doc():
    """Get a document from DocuSign

    query parameters: url, fn
    Returns {err, pdf, filename}
    """
    err = False # No problems so far!
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    uri = request.args.get("url")
    fn = request.args.get("fn")

    if not uri:
        return {"err": "query parameter url is missing!"}

    # Retrieve file
    # append the uri parameter to the baseUrl and use in the request
    url = auth["base_url"] + uri
    ds_headers = {'Accept': 'Accept: application/pdf', auth["auth_header_key"]: auth["auth_header_value"]}

    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling EnvelopeViews:createRecipient: " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error retrieving document.<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    # Success!
    return {"err": err, "pdf": r.content, "filename": fn}




# FIN
    















