# DocuSign API List Envelope Status Recipe 005 (PYTHON)
# coding=UTF-8

# Set encoding to utf8. See http://stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, socket, certifi, requests, os, base64, re, urllib, shutil, datetime
# See http://requests.readthedocs.org/ for information on the requests library
# See https://urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

from app.lib_master_python import ds_recipe_lib
from app.lib_master_python import ds_webhook
from flask import  session

trace_value = "py_005_list_envelope_status" # Used for tracing API calls
trace_key = "X-ray"
intro = ("<h2>Envelope: listStatusChanges</h2>" +
    "<p>List the envelope status changes since a date and time. Can be used to poll for status changes.</p>" +
    "<p>See <a href='https://docs.docusign.com/esign/guide/usage/status_and_events.html' target='_blank'>docs</a> " +
    "for information on a polling strategy that won’t break the platform’s polling policy.</p>"
    )

def start():
    """Sends Envelopes: listStatusChanges method

    Returns r: {
        err: False, or an error message
        intro: html introduction to the page
        url: the url used for the request
        response: the response body
        }
    """

    # Ready...

    # STEP 1 - Fetch Authentication information from session
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    #
    # STEP 2 - Create and send the request
    #
    
    # See the docs, https://docs.docusign.com/esign/restapi/Envelopes/Envelopes/listStatusChanges/
    # We need to set one or more of the following parameters: from_date, envelopeIds and/or transactionIds.
    # We will set from_date to be yesterday.
    #
    # If you're using this method to poll for changes, see "Polling for Current Status" section of 
    # page https://docs.docusign.com/esign/guide/usage/status_and_events.html for a strategy that won't
    # violate the platform's polling policy.
    
    # construct the body of the request
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_s = yesterday.strftime ("%Y-%m-%d") # '2016-07-25'
        
    # create the url from the baseUrl
    url = auth["base_url"] + "/envelopes?from_date={}".format(yesterday_s)
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"],
                  trace_key: trace_value}

    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Envelopes:listStatusChanges: " + str(e)}
        
    status = r.status_code
    if (status != 200): 
        return ({'err': "Error calling DocuSign Envelopes:listStatusChanges<br/>Status is: " +
            str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    response = r.json()
    return {
        "err": False,
        "url": url,
        "intro": intro,
        "response": json.dumps(response, indent=4, sort_keys=True)
    }

########################################################################
########################################################################

# FIN
    















