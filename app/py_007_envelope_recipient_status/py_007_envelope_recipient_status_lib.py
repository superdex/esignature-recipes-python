# DocuSign API Envelope Recipient Status Recipe 007 (PYTHON)
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

trace_value = "py_007_envelope_recipient_status" # Used for tracing API calls
trace_key = "X-ray"
intro = ("<h2>EnvelopeRecipients: list</h2>" +
    "<p>This recipe fetches the current status for an envelope’s recipients.</p>" +
    "<p>The recipient status for last envelope that you sent with any of this tool’s other recipes will be fetched.</p>"
    )

def start():
    """Sends EnvelopeRecipients: list method

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
        
    if not 'latest_envelope_id' in session:
        return {"err": "Problem, no envelope ID is available. Please send an envelope with a different recipe, then retry the Envelope Recipient Status recipe."}
    envelope_id = session['latest_envelope_id']

    #
    # STEP 2 - Create and send the request
    #
    # See the docs, https://docs.docusign.com/esign/restapi/Envelopes/EnvelopeRecipients/list
            
    # create the url from the baseUrl
    url = auth["base_url"] + "/envelopes/{}/recipients/?include_tabs=true".format(envelope_id)
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"],
                  trace_key: trace_value}

    try:
        r = requests.get(url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling EnvelopeRecipients:list: " + str(e)}
        
    status = r.status_code
    if (status != 200): 
        return ({'err': "Error calling DocuSign EnvelopeRecipients:list<br/>Status is: " +
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
