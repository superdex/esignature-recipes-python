# DocuSign webhook library
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import os, base64, json

from app.lib_master_python import ds_recipe_lib
from flask import request, session
from bs4 import BeautifulSoup

webhook_path = "/webhook"
xml_file_dir = "app/static/files/"
doc_prefix = "doc_"
heroku_env = 'DYNO' # Used to detect if we're on Heroku

########################################################################
########################################################################
#
# This module takes care of the session["webhook"] data.
# It stores:
#   enabled: True/False
#   status: {
#       yes: use the listener_url
#       no: User has told us to not use the webhook
#       ask: Ask the User what we should do.
#
#   listener_url: the complete listener url used by the DocuSign platform to send us notifications
#                 It must be accessible from the public internet
#   url_begin: the part of the path that might be changed
#   url_end: the last bit that won't change. Eg /webhook


def get_webhook_status():
    """Returns the webhook status of the current session

    Side-effect: initializes webhook setting

    Returns:
    webhook_status = {
        status:
            yes: use the listener_url
            no: User has told us to not use the webhook
            ask: Ask the User what we should do.
        listener_url # The complete listener url that we're planning to use
        url_begin: the part of the path that might be changed
        url_end: the last bit that won't change. Eg /webhook

        }
    """

    if 'webhook' in session:
        webhook = session['webhook']
    else:
        webhook = webhook_default()
        session['webhook'] = webhook # Set it!

    return {
            'status': webhook['status'],
            'url_begin': webhook['url_begin'],
            'url_end': webhook['url_end'],
            'listener_url': webhook['listener_url']
        }

def webhook_default():
    """Initialize the webook settings. If on Heroku, then default to enabled"""
    on_heroku = heroku_env in os.environ

    if on_heroku:
        webhook = {
            'enabled': True,
            'status': 'yes',
            'url_begin': ds_recipe_lib.get_base_url(1),
            'url_end': webhook_path,
            'listener_url': ds_recipe_lib.get_base_url(1) + webhook_path
        }
    else:
        webhook = {
            'enabled': False,
            'status': 'ask',
            'url_begin': ds_recipe_lib.get_base_url(1),
            'url_end': webhook_path,
            'listener_url': False
        }
    return webhook


def eventNotificationObj():
    """Return false or an eventNotification object that should be added to an Envelopes: create call

    Uses the session["webhook"] object to determine the situation
    """

    webhook_url = ds_recipe_lib.get_base_url() + webhook_path
    event_notification = {"url": webhook_url,
        "loggingEnabled": "true", # The api wants strings for true/false
        "requireAcknowledgment": "true",
        "useSoapInterface": "false",
        "includeCertificateWithSoap": "false",
        "signMessageWithX509Cert": "false",
        "includeDocuments": "true",
        "includeEnvelopeVoidReason": "true",
        "includeTimeZone": "true",
        "includeSenderAccountAsCustomField": "true",
        "includeDocumentFields": "true",
        "includeCertificateOfCompletion": "true",
        "envelopeEvents": [ # for this recipe, we're requesting notifications
            # for all envelope and recipient events
            {"envelopeEventStatusCode": "sent"},
            {"envelopeEventStatusCode": "delivered"},
            {"envelopeEventStatusCode": "completed"},
            {"envelopeEventStatusCode": "declined"},
            {"envelopeEventStatusCode": "voided"}],
        "recipientEvents": [
            {"recipientEventStatusCode": "Sent"},
            {"recipientEventStatusCode": "Delivered"},
            {"recipientEventStatusCode": "Completed"},
            {"recipientEventStatusCode": "Declined"},
            {"recipientEventStatusCode": "AuthenticationFailed"},
            {"recipientEventStatusCode": "AutoResponded"}]
        }
    return event_notification

def foo():
    # Instructions for reading the email
    html =  ("<h2>Signature request sent!</h2>" +
            "<p>Envelope ID: " + envelope_id + "</p>" +
            "<p>Signer: " + ds_signer1_name + "</p>" +
            "<p>CC: " + ds_cc1_name + "</p>" +
            "<h2>Next steps</h2>" +
            "<h3>1. View the incoming notifications and documents</h3>" +
            "<p><a href='" + ds_recipe_lib.get_base_url() + "/status_page/" + envelope_id + "'" +
            "  class='btn btn-primary' role='button' target='_blank' style='margin-right:1.5em;'>" +
            "View Notification Files</a> (A new tab/window will be used.)</p>" +
            "<h3>2. Respond to the Signature Request</h3>")

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

    html += "<p>Webhook url: " + webhook_url + "</p>"

    return {"ok": True,
        "envelope_id": envelope_id,
        "ds_signer1_email": ds_signer1_email,
        "ds_signer1_name": ds_signer1_name,
        "ds_signer1_access": ds_signer1_email_access,
        "ds_signer1_qr": ds_signer1_email,
        "ds_cc1_email": ds_cc1_email,
        "ds_cc1_name": ds_cc1_name,
        "webhook_url": webhook_url,
        "html": html
    }
    
########################################################################
########################################################################

def status_page(envelope_id):
    # Get envelope information
    # Calls GET /accounts/{accountId}/envelopes/{envelopeId}
    
    url = ds_recipe_lib.ds_base_url + "/envelopes/" + envelope_id
    ds_params = json.dumps(
            {"status_envelope_id": envelope_id, "url": ds_recipe_lib.get_base_url(2)})
    result = {'ok': True, 'msg': None}

    r = ds_recipe_lib.login()
    if (not r["ok"]):
        result = {'ok': False, 'msg': "Error logging in"}
        return {"result": result, "ds_params": ds_params}
    try:
        r = requests.get(url, headers=ds_recipe_lib.ds_headers)
    except requests.exceptions.RequestException as e:
        result = {'ok': False, 'msg': "Error calling Envelopes:get: " + str(e)}
        return {"result": result, "ds_params": ds_params}
        
    status = r.status_code
    if (status != 200): 
        result = {'ok': False, 'msg': "Error calling DocuSign Envelopes:get, status is: " + str(status)}
        return {"result": result, "ds_params": ds_params}

    return {"result": result, "envelope": r.json(), "ds_params": ds_params}

########################################################################
########################################################################

def status_items(envelope_id):
    # List of info about the envelope's event items received
    files_dir_url = ds_recipe_lib.get_base_url(2) + "/static/files/" + envelope_id_to_dir(envelope_id)
    env_dir = get_envelope_dir(envelope_id)
    results = []
    if (not os.path.isdir(env_dir)):
        return results # early return. 
        
    for i in os.listdir(env_dir):
        if i.endswith(".xml"): 
            results.append(status_item(os.path.join(env_dir, i), i, files_dir_url))
        continue

    return results

########################################################################
########################################################################

def status_item(filepath, filename, files_dir_url):
    # summary information about the notification
    
    f = open(filepath)
    data = f.read()
                      
    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/

    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string
    
    # iterate through the recipients
    recipients = []
    for recipient in xml.EnvelopeStatus.RecipientStatuses.children:
        if (recipient.string == "\n"):
            continue
        recipients.append({
            "type": recipient.Type.string,
            "email": recipient.Email.string,
            "user_name": recipient.UserName.string,
            "routing_order": recipient.RoutingOrder.string,
            "sent_timestamp": get_string(recipient.Sent),
            "delivered_timestamp": get_string(recipient.Delivered),
            "signed_timestamp": get_string(recipient.Signed),
            "status": recipient.Status.string
        })
        
    documents = [];
    # iterate through the documents if the envelope is Completed
    if (xml.EnvelopeStatus.Status.string == "Completed" and xml.DocumentPDFs):
        for pdf in xml.DocumentPDFs.children:
            if (pdf.string == "\n"):
                continue
            doc_filename = get_pdf_filename(pdf.DocumentType.string, pdf.Name.string)
            documents.append({
                "document_ID": get_string(pdf.DocumentID),
                "document_type": pdf.DocumentType.string,
                "name": pdf.Name.string,
                "url": files_dir_url + '/' + doc_filename
            })
        
    result = {
        "envelope_id": envelope_id,
        "xml_url": files_dir_url + '/' + filename,
        "time_generated": xml.EnvelopeStatus.TimeGenerated.string,
        "subject": xml.EnvelopeStatus.Subject.string,
        "sender_user_name": xml.EnvelopeStatus.UserName.string,
        "sender_email": get_string(xml.EnvelopeStatus.Email),
        "envelope_status": xml.EnvelopeStatus.Status.string,
        "envelope_sent_timestamp": xml.EnvelopeStatus.Sent.string,
        "envelope_created_timestamp": xml.EnvelopeStatus.Created.string,
        "envelope_delivered_timestamp": get_string(xml.EnvelopeStatus.Delivered),
        "envelope_signed_timestamp": get_string(xml.EnvelopeStatus.Signed),
        "envelope_completed_timestamp": get_string(xml.EnvelopeStatus.Completed),
        "timezone": xml.TimeZone.string,
        "timezone_offset": xml.TimeZoneOffset.string,
        "recipients": recipients,
        "documents": documents}
    
    return result


def get_string(element):
    return None if element == None else element.string
    

########################################################################
########################################################################

def setup_output_dir(envelope_id):
# setup output dir for the envelope
    # Store the file. Create directories as needed
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E and the timestamps with T
    
    # Make the envelope's directory
    
    envelope_dir = get_envelope_dir(envelope_id)
    os.makedirs(envelope_dir)

def get_envelope_dir(envelope_id):
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E
    
    # Make the envelope's directory
    files_dir = os.path.join(os.getcwd(), xml_file_dir)
    envelope_dir = os.path.join(files_dir, envelope_id_to_dir(envelope_id))
    return envelope_dir

def envelope_id_to_dir(envelope_id):
    return "E" + envelope_id

########################################################################
########################################################################

def webhook_listener():
    # Process the incoming webhook data. See the DocuSign Connect guide
    # for more information
    #
    # Strategy: examine the data to pull out the envelope_id and time_generated fields.
    # Then store the entire xml on our local file system using those fields.
    #
    # If the envelope status=="Completed" then store the files as doc1.pdf, doc2.pdf, etc
    #
    # This function could also enter the data into a dbms, add it to a queue, etc.
    # Note that the total processing time of this function must be less than
    # 100 seconds to ensure that DocuSign's request to your app doesn't time out.
    # Tip: aim for no more than a couple of seconds! Use a separate queuing service
    # if need be.

    data = request.data # This is the entire incoming POST content.
                        # This is dependent on your web server. In this case, Flask
      
    # f = open(os.getcwd() + "/app/example_completed_notification.xml")
    # data = f.read()
                      
    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/

    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string
    time_generated = xml.EnvelopeStatus.TimeGenerated.string

    # Store the file.     
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the envelope ids with E and the timestamps with T
    setup_output_dir(envelope_id)
    envelope_dir = get_envelope_dir(envelope_id)
    filename = "T" + time_generated.replace(':' , '_') + ".xml" # substitute _ for : for windows-land
    filepath = os.path.join(envelope_dir, filename)
    with open(filepath, "w") as xml_file:
        xml_file.write(data)
    
    # If the envelope is completed, pull out the PDFs from the notification XML
    if (xml.EnvelopeStatus.Status.string == "Completed"):
        # Loop through the DocumentPDFs element, storing each document.
        for pdf in xml.DocumentPDFs.children:
            filename = get_pdf_filename(pdf.DocumentType.string, pdf.Name.string)
            full_filename = os.path.join(envelope_dir, filename)
            with open(full_filename, "wb") as pdf_file:
                pdf_file.write(base64.b64decode(pdf.PDFBytes.string))

########################################################################
########################################################################

def get_pdf_filename(doc_type, pdf_name):
    if (doc_type == "CONTENT"):
        filename = 'Completed_' + pdf_name
    elif (doc_type == "SUMMARY"):
        filename = pdf_name
    else:
        filename = doc_type + "_" + pdf_name
    
    return filename

########################################################################
########################################################################

def nda_fields():
    # The fields for the sample document "NDA"
    # Create 4 fields, using anchors 
    #   * signer1sig
    #   * signer1name
    #   * signer1company
    #   * signer1date
    fields = {
    "signHereTabs": [{
        "anchorString": "signer1sig",
        "anchorXOffset": "0",
         "anchorYOffset": "0",
        "anchorUnits": "mms",
        "recipientId": "1",
        "name": "Please sign here",
        "optional": "false",
        "scaleValue": 1,
        "tabLabel": "signer1sig"}],
    "fullNameTabs": [{
        "anchorString": "signer1name",
         "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Full Name",
        "name": "Full Name"}],
    "textTabs": [{
        "anchorString": "signer1company",
         "anchorYOffset": "-8",
        "fontSize": "Size12",
        "recipientId": "1",
        "tabLabel": "Company",
        "name": "Company",
        "required": "false"}],
    "dateSignedTabs": [{
        "anchorString": "signer1date",
         "anchorYOffset": "-6",
        "fontSize": "Size12",
        "recipientId": "1",
        "name": "Date Signed",
             "tabLabel": "Company"}]
    }
    return fields

########################################################################
########################################################################

# FIN
