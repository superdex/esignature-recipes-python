# DocuSign webhook library
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import os, base64, json, requests, logging

from app.lib_master_python import ds_recipe_lib
from flask import request, session
from bs4 import BeautifulSoup

webhook_path = "/webhook"
xml_file_dir = "app/static/files/"
doc_prefix = "doc_"
heroku_env = 'DYNO' # Used to detect if we're on Heroku
trace_value = "py_webhook" # Used for tracing API calls
trace_key = "X-ray"

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
        err: False or a problem string.
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
            'err': False,
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

def set_webhook_status():
    """Enables the webhook status to be set for the session.

    The Request body:
    webhook_status, url_begin

    The Response:
    Same as from get_webhook_status
    """

    req = request.get_json()
    webhook_status = req["webhook_status"]
    url_begin = req["url_begin"]

    if not (webhook_status=="no" or webhook_status == "yes"):
        return {"err": "Please select a webhook status"}
    if len(url_begin) < 7:
        return {"err": "Please enter a server address, including http or https"}

    webhook = {
        'enabled': webhook_status == "yes",
        'status': webhook_status,
        'url_begin': url_begin,
        'url_end': webhook_path,
        'listener_url': url_begin + webhook_path
    }
    session["webhook"] = webhook # Set it!

    return {
        'err': False,
        'status': webhook['status'],
        'url_begin': webhook['url_begin'],
        'url_end': webhook['url_end'],
        'listener_url': webhook['listener_url']
    }


def get_eventNotification_object():
    """Return false or an eventNotification object that should be added to an Envelopes: create call

    Uses the session["webhook"] object to determine the situation
    """

    webhook = session['webhook']
    if not webhook['enabled']:
        return False

    webhook_url = webhook['listener_url']
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
            {"envelopeEventStatusCode": "draft"},
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

def webhook_instructions(envelope_id):
    """ Instructions for reading the notifications"""
    html =  ("<h3>1. View the incoming notifications and documents</h3>" +
            "<p><a href='" + ds_recipe_lib.get_base_url(2) + "/webhook_status_page/" + envelope_id + "'" +
            "  class='btn btn-primary wh' role='button' target='_blank'>" +
            "View Webhook Notifications</a> (A new tab/window will be used.)</p>")

    webhook = session['webhook']
    if not webhook['enabled']:
        return False
    else:
        return html

########################################################################
########################################################################

def status_page(envelope_id):
    """Information for the status (notifications) page

    Returns:
        err: False or an error msg
        envelope: The envelope status info received
        ds_params: JSON string format for use by the Javascript on the page.
            {status_envelope_id, url}  # url is the base url for this app
    """

    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    # Calls Envelopes: get. See https://docs.docusign.com/esign/restapi/Envelopes/Envelopes/get/
    # Calls GET /accounts/{accountId}/envelopes/{envelopeId}
    url = auth["base_url"] + "/envelopes/{}".format(envelope_id)
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"],
        trace_key: trace_value}
    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Templates:list: " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign Envelopes:get<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    ds_params = json.dumps(
        {"status_envelope_id": envelope_id, "url": ds_recipe_lib.get_base_url(2)})
    return {"err": False, "envelope": r.json(), "ds_params": ds_params}

########################################################################
########################################################################

def status_items(envelope_id):
    """List of info about the envelope's event items that were received"""
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
    """summary information about the notification"""
    
    f = open(filepath)
    data = f.read()

    # Note, there are many options for parsing XML in Python
    # For this recipe, we're using Beautiful Soup, http://www.crummy.com/software/BeautifulSoup/
    xml = BeautifulSoup(data, "xml")
    envelope_id = xml.EnvelopeStatus.EnvelopeID.string

    # Get envelope's attributes. Since the recipients also have "Status" we CAN NOT just use
    # xml.EnvelopeStatus.Status.string since that returns the first Status *descendant* of EnvelopeStatus
    # (We want the first child). So we get the children this way:
    #
    # Set defaults for fields that may not be present
    time_generated = subject = sender_user_name = sender_email = envelope_sent_timestamp = envelope_created_timestamp = None
    envelope_delivered_timestamp = envelope_signed_timestamp = envelope_completed_timestamp = None

    # Now fill in the values that we can find:
    for child in xml.EnvelopeStatus:
        if child.name == "Status": envelope_status = child.string
        if child.name == "TimeGenerated": time_generated = child.string
        if child.name == "Subject": subject = child.string
        if child.name == "UserName": sender_user_name = child.string
        if child.name == "Email": sender_email = child.string
        if child.name == "Sent": envelope_sent_timestamp = child.string
        if child.name == "Created": envelope_created_timestamp = child.string
        if child.name == "Delivered": envelope_delivered_timestamp = child.string
        if child.name == "Signed": envelope_signed_timestamp = child.string
        if child.name == "Completed": envelope_completed_timestamp = child.string

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
        
    documents = []
    # iterate through the documents if the envelope is Completed
    if envelope_status == "Completed" and xml.DocumentPDFs:
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
        "time_generated": time_generated,
        "subject": subject,
        "sender_user_name": sender_user_name,
        "sender_email": sender_email,
        "envelope_status": envelope_status,
        "envelope_sent_timestamp": envelope_sent_timestamp,
        "envelope_created_timestamp": envelope_created_timestamp,
        "envelope_delivered_timestamp": envelope_delivered_timestamp,
        "envelope_signed_timestamp": envelope_signed_timestamp,
        "envelope_completed_timestamp": envelope_completed_timestamp,
        "timezone": xml.TimeZone.string,
        "timezone_offset": xml.TimeZoneOffset.string,
        "recipients": recipients,
        "documents": documents}

    return result

def get_string(element):
    """Helper for safely pulling string from XML"""
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
    try:
        os.makedirs(envelope_dir)
    except OSError as e:
        if e.errno != 17: # FileExists error
            raise
        pass

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

# FIN
