# DocuSign api_logging library
#
# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import os, base64, json, requests, shutil, datetime, zipfile, StringIO

from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_authentication
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
        err_code: False or codes eg 'GENERIC', 'PLEASE_AUTHENTICATE', 
        status: string description of the status
        logging: True / False
        remaining_entries: integer from the platform,
        max_entries: integer from the platform
        }
    """

    global auth
    auth = ds_authentication.get_auth()
    if auth["err"]:
        return {"err": auth["err"], "err_code": auth["err_code"]}
            
    logging = logging_updateSettings() # returns {err, max_entries, remaining_entries, err_code}
    if logging['err']:
        return {"err": logging["err"]}

    # No API error...
    if logging["logging"]:
        logging_activated = "Logging is activated. "
    else:
        logging_activated = "Logging is <b>not</b> activated! "
    status = logging_activated + "{} logging spaces are available out of {} total.".format(
        logging["remaining_entries"], logging["max_entries"])
    return {
            'err': False,
            'status': status,
            'logging': logging["logging"],
            'remaining_entries': logging["remaining_entries"],
            'max_entries': logging["max_entries"]
        }
        
def delete_logs():
    """Delete all local log files
    
    Returns {err}
    """
    
    log_path = get_log_path()
    try:
        shutil.rmtree(log_path) # Remove the dir and contents
    except OSError as e:
        if e.errno != 2: # No such file or directory
            raise
        pass
    make_deep_dir (log_path)
    return {"err": False}

def logging_updateSettings():
    """Request logging and get current status

    Returns {err, max_entries, remaining_entries, err_code}
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
    if int(data["apiRequestLogRemainingEntries"]) < 0:
        data["apiRequestLogRemainingEntries"] = 0 # Sometimes the platform returns negative numbers!
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
    global auth
    auth = ds_authentication.get_auth()
    if auth["err"]:
        return {"err": auth["err"], "err_code": auth["err_code"]}
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

    Returns {err: False or a problem string, entries: log_entries, err_code }
        returns an array of just the new log_entries
    """
    global auth
    auth = ds_authentication.get_auth()
    if auth["err"]:
        return {"err": auth["err"], "err_code": auth["err_code"]}
    r = logging_do_download() # returns {err, new_entries}
    return r

def logging_do_download():
    """Download the current logging entries and store them

    Returns {err, entries, new_entries, err_code}
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
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>",
                  'err_code': status})

    z = zipfile.ZipFile(StringIO.StringIO(r.content))
    z.extractall(temp_log_path)

    entries = process_new_log_entries()

    # Now delete the entries on the platform
    # See https://docs.docusign.com/esign/restapi/Diagnostics/RequestLogs/updateSettings
    # url = auth["base_url_no_account"] + "/diagnostics/request_logs"
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    try:
        r = requests.delete(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling RequestLogs:delete " + str(e)}
    
    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign RequestLogs:delete<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})
    
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

# FIN
