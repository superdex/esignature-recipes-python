# DocuSign api_logging library
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import os, base64, json, requests, shutil, datetime, zipfile, StringIO

from app.lib_master_python import ds_recipe_lib
from flask import request, session
from bs4 import BeautifulSoup

log_storage_uri = "static/files/logs"
log_storage_dir = "app/" + log_storage_uri
session_log_path = "log_path"
auth = False # Global auth session information

########################################################################
########################################################################
#
# This module manages API logging
# It works with the platform logging methods:
# https://docs.docusign.com/esign/restapi/Diagnostics/RequestLogs/
#
# It stores log_path in the session
#

def get_logging_status():
    """Returns the logging status of the account

    Side-effect: initializes logging if it isn't already active

    Returns:
    logging_status = {
        err: False or a problem string.
        status: string description of the status
        logging: True / False
        remaining_entries: integer from the platform,
        max_entries: integer from the platform
        }
    """

    if not check_auth():
        return {"err": "Please authenticate."}
    logging = logging_updateSettings() # returns {err, max_entries, remaining_entries}
    if logging['err']:
        return {"err": logging["err"]}

    # No API error...
    if logging["logging"]:
        logging_activated = "Logging is activated. "
    else:
        logging_activated = "Logging is <b>not</b> activated! "
    status = logging_activated + "{} logging entries are available out of {} total.".format(logging["remaining_entries"], logging["max_entries"])
    return {
            'err': False,
            'status': status,
            'logging': logging["logging"],
            'remaining_entries': logging["remaining_entries"],
            'max_entries': logging["max_entries"]
        }

def check_auth():
    global auth
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return False
    else:
        return False

    return True

def logging_updateSettings():
    """Request logging and get current status

    Returns {err, max_entries, remaining_entries}
    """

    # See https://docs.docusign.com/esign/restapi/Diagnostics/RequestLogs/updateSettings
    url = auth["base_url_no_account"] + "/diagnostics/settings"
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    data = {"apiRequestLogging": "true"}

    try:
        r = requests.put(url, headers=ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling RequestLogs:updateSettings " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign RequestLogs:updateSettings<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    data = r.json()
    return {"err": False, "max_entries": data["apiRequestLogMaxEntries"],
            "remaining_entries": data["apiRequestLogRemainingEntries"],
            "logging": data["apiRequestLogging"]}

def logs_list():
    """Returns log_entries for all current logs that were previously downloaded

    {"err": an error or false
     "entries": Array of log_entry
     log_entry: {file_name: the filename of the entry
                url: for retrieving the file
                head: first 1500 bytes of the entry, base64 encoded}
    }
    Strategy: parse the log files on the clients.
    """
    if not check_auth():
        return {"err": "Please authenticate."}
    entries = []
    log_path = get_log_path()
    log_path_url = ds_recipe_lib.get_base_url(1) + "/" + log_storage_uri + "/" + account_id_to_dir(auth["account_id"]) + "/"

    # Walk the dir
    for i in os.listdir(log_path):
        if i.endswith(".txt"):
            entries.append(api_log_item(os.path.join(log_path, i), i, log_path_url))
    return {"err": False, "entries": entries}

def logs_download():
    """Download (and then delete) the logs from DocuSign

    The logs are stored in files/log/<account_id>/log_<timestamp>_<orig_name>
    <orig_name> is the original name of the file from the platform. Eg:
        00_OK_GetAccountSharedAccess.txt
        01_OK_GetFolderList.txt
        02_OK_ExecuteLoggedApiBusinessLogic.txt
        03_Created_RequestRecipientToken.txt
        04_OK_GetEnvelope.txt
        05_OK_GetEnvelope.txt
        06_OK_SendEnvelope.txt

    Returns {err: False or a problem string, entries: log_entries }
        returns an array of just the new log_entries
    """
    if not check_auth():
        return {"err": "Please authenticate."}
    r = logging_do_download() # returns {err, new_entries}
    return r

def logging_do_download():
    """Download the current logging entries and store them

    Returns {err, entries, new_entries}
    """
    global auth
    # See https://docs.docusign.com/esign/restapi/Diagnostics/RequestLogs/list/

    temp_log_path = clear_temp_log_path()
    url = auth["base_url_no_account"] + "/diagnostics/request_logs"
    ds_headers = {'Accept': 'application/zip', auth["auth_header_key"]: auth["auth_header_value"]}

    try:
        r = requests.get(url, headers=ds_headers, stream=True)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling RequestLogs:request_logs " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign RequestLogs:request_logs<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    z = zipfile.ZipFile(StringIO.StringIO(r.content))
    z.extractall(temp_log_path)

    entries = process_new_log_entries()

    # Now delete the entries on the platform
    # See https://docs.docusign.com/esign/restapi/Diagnostics/RequestLogs/updateSettings
    # url = auth["base_url_no_account"] + "/diagnostics/request_logs"
    # ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    ##try:
    ##    r = requests.delete(url, headers=ds_headers)
    ##except requests.exceptions.RequestException as e:
    ##    return {'err': "Error calling RequestLogs:delete " + str(e)}
    ##
    ##status = r.status_code
    ##if (status != 200):
    ##    return ({'err': "Error calling DocuSign RequestLogs:delete<br/>Status is: " +
    ##                    str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})
    ##
    return {"err": False, "entries": entries}

def process_new_log_entries():
    """Process the new log entries in the temp dir.

    Returns the entries"""
    entries = []
    temp_log_path = get_temp_log_path()
    log_path = get_log_path()
    time = datetime.datetime.now()
    time = time.replace(microsecond=0) # clear the microseconds
    time = time.isoformat() # Convert to string. Eg '2016-07-17T10:24:03'
    time = "T" + time.replace(':' , '_') # substitute _ for : for windows-land eg. 'T2016-07-17T10_24_03'
    log_path_url = ds_recipe_lib.get_base_url(1) + "/" + log_storage_uri + "/" + account_id_to_dir(auth["account_id"]) + "/"

    # Walk the dir
    for i in os.listdir(temp_log_path):
        if i.endswith(".txt"):
            new_file_name = time + "__" + i
            new_path = os.path.join(log_path, new_file_name)
            os.rename(os.path.join(temp_log_path, i), new_path)
            entries.append(api_log_item(new_path, new_file_name, log_path_url))
    return entries

def api_log_item(file_path, file_name, log_path_url):
    """Create a log item from the file

    Returns: {
        file_name: the filename of the entry
        url: for retrieving the file
        head: first 1500 bytes of the log file, base64 encoded
    }
    """
    with open(file_path, "rb") as f:
        head = f.read(1500)

    return {
        'file_name': file_name,
        'url': log_path_url + file_name,
        'head': base64.b64encode(head)
    }

def get_temp_log_path():
    """Returns the temp log path for this account"""
    if session_log_path in session:
        log_path = session[session_log_path]
    else:
        log_path = create_log_path()
    path = os.path.join(log_path, "TEMP")
    return path

def clear_temp_log_path():
    """Clears, then Returns the temp log path for this account"""
    path = get_temp_log_path()
    try:
        shutil.rmtree(path) # Remove the temp dir and contents
    except OSError as e:
        if e.errno != 2: # No such file or directory
            raise
        pass
    make_deep_dir(path) # Create
    return path

def get_log_path():
    """Returns the log path for this account"""
    if session_log_path in session:
        log_path = session[session_log_path]
    else:
        log_path = create_log_path()
    return log_path

def create_log_path():
    """Create the path for the zip files for this account

    The path is stored in the session as log_path"""
    account_id = auth["account_id"]
    setup_output_dir(account_id)
    path = get_account_dir(account_id)
    session[session_log_path] = path
    return path














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
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
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
    sender_email = envelope_delivered_timestamp = envelope_created_timestamp = envelope_signed_timestamp =  None
    envelope_completed_timestamp = None
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

def setup_output_dir(account_id):
# setup output dir for the account
    # Store the file. Create directories as needed
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the account_ids with A and the timestamps with T
    
    # Make the account's directory
    account_dir = get_account_dir(account_id)
    make_deep_dir(account_dir)

def make_deep_dir (dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != 17:  # FileExists error
            raise
        pass

def get_account_dir(account_id):
    # Some systems might still not like files or directories to start with numbers.
    # So we prefix the account ids with A
    
    # Make the account's directory
    files_dir = os.path.join(os.getcwd(), log_storage_dir)
    account_dir = os.path.join(files_dir, account_id_to_dir(account_id))
    return account_dir

def account_id_to_dir(account_id):
    return "A" + account_id

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
