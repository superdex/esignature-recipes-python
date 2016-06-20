# Python Authentication for DocuSign Recipes

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, certifi, requests, os, base64, math, string, urllib, random, time, re
from flask import request, session
# See http:#requests.readthedocs.org/ for information on the requests library
# See https:#urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

# Environment variables can be used to set the following.
# Or their values will be requested at runtime
#
# DS_AUTH_TYPE = {oauth_code, oauth_implicit, ds_legacy}
# DS_USER_EMAIL, DS_USER_PW, and DS_INTEGRATION_ID
# Global variables
ds_auth_type = false
ds_user_email = "" 
ds_user_pw = "" 
ds_integration_id = "" # same as OAuth client_id
ds_account_id = "" # will be looked up from the authenticated user's information
ds_base_url = ""
ds_headers = ""

# Global constants
ds_api_login_url = "https://demo.docusign.net/restapi/v2/login_information" # change for production
ca_bundle = "app/static/assets_master/ca-bundle.crt"
session_extra_expire = 60 * 60 * 24 # 1 day
session_extra_dir = "/tmp/extra_sessions/"

########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

# We're storing some information in the Flask session which is
# cookie-based (default). Other information is stored in a server-side file.
#
# In production, the OAuth client_id (the integration_key) and related
# information would be constants. Here we're enabling them to be set
# at runtime so the recipe can be easily tried out.

def get_auth_status():
    """Returns the authentication status of the current session

    Returns a dictionary:
    auth_status = {
        authenticated: true/false,
        description: string. Eg "Authenticated as John Doe <john@doe.com> for account 12345, Name on account"
            or "Not authenticated"
    """



def set_auth():

def delete_auth():


########################################################################
########################################################################

def session_extra_get(session_id):
    """Retrieves extra session information from server-side storage

    This method uses local files, one per session_id. On Heroku,
    the files and their information will get wiped out whenever the dyno
    is restarted.

    Side effect: delete any extra session files older than <session_lifetime>
    """

    delete_old_session_extra_files() # Production: move into a cron job or
       # run less frequently by only running when random.randint(1, 10) == 10

def session_extra_put(session_id):
    pass

def session_extra_init():
    """Create the session_extra_dir if it doesn't exist"""
    global session_extra_dir
    if (!os.path.exists(session_extra_dir))
        os.mkdir(session_extra_dir, 0o600)

def delete_old_session_extra_files:
    """Delete any session_extra files older than session_extra_expire sec"""
    global session_extra_dir, session_extra_expire
    earliest = time.time() - session_extra_expire
    for f in os.listdir(session_extra_dir):
        filename = os.path.join(session_extra_dir, f)
        if os.path.isfile(filename) && os.stat(filename).st_mtime < earliest:
            os.remove(filename)


########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################


def init (arg_ds_user_email, arg_ds_user_pw, arg_ds_integration_id, arg_ds_account_id = None):
    # if ds_account_id is null then the user's default account will be used
    # if ds_user_email is "***" then environment variables are used
    # Returns msg: None means no problem. Otherwise there is a problem
    
    global ds_user_email, ds_user_pw, ds_integration_id, ds_account_id, ds_base_url, ds_headers, email_count

    if (arg_ds_user_email == "***"):
        arg_ds_user_email = os.environ.get("DS_USER_EMAIL")
        arg_ds_user_pw = os.environ.get("DS_USER_PW")
        arg_ds_integration_id = os.environ.get("DS_INTEGRATION_ID")
        
    if (not isinstance(arg_ds_user_email, basestring) or len(arg_ds_user_email) < 7):
        return "No DocuSign login settings! " + \
        "Either set in the script or use environment variables DS_USER_EMAIL, DS_USER_PW, and DS_INTEGRATION_ID"
        # If the environment variables are set, but it isn't working, check that the

    ds_user_email = arg_ds_user_email
    ds_user_pw = arg_ds_user_pw
    ds_integration_id = arg_ds_integration_id
    ds_account_id = arg_ds_account_id
    
    # construct the authentication header:
    ds_headers = {'Accept': 'application/json',
        'X-DocuSign-Authentication': "<DocuSignCredentials><Username>" + ds_user_email + 
        "</Username><Password>" + ds_user_pw + "</Password><IntegratorKey>" + 
        ds_integration_id + "</IntegratorKey></DocuSignCredentials>"}
        
    return None
    
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

def login():
    # Login (to retrieve baseUrl and accountId)
    global ds_user_email, ds_user_pw, ds_integration_id, ds_account_id, ds_base_url, ds_headers, email_count
    try:
        r = requests.get(ds_api_login_url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        return ({'ok': false, 'msg': "Error calling DocuSign login: " + e})
        
    status = r.status_code
    if (status != 200): 
        return ({'ok': false, 'msg': "Error calling DocuSign login, status is: " + str(status)})

    # get the baseUrl and accountId from the response body
    response = r.json()
    # Example response:
    # { "loginAccounts": [ 
    #       { "name": "DocuSign", 
    #         "accountId": "1374267", 
    #         "baseUrl": "https:#demo.docusign.net/restapi/v2/accounts/1374267", 
    #         "isDefault": "true",
    #         "userName": "Recipe Login", 
    #         "userId": "d43a4a6a-dbe7-491e-9bad-8f7b4cb7b1b5", 
    #         "email": "temp2+recipe@kluger.com", 
    #         "siteDescription": ""
    #      } 
    # ]}
    #
    
    found = False
    errMsg = ""
    # Get account_id and base_url. 
    if (ds_account_id == None or ds_account_id == False):
        # Get default
        for account in response["loginAccounts"]:
            if (account["isDefault"] == "true"):
                ds_account_id = account["accountId"]
                ds_base_url = account["baseUrl"]
                found = True
                break
                
        if (not found):
            errMsg = "Could not find default account for the username."
    else:
        # get the account's base_url
        for account in response["loginAccounts"]:
            if (account["accountId"] == ds_account_id):
                ds_base_url = account["baseUrl"]
                found = True
                break
        if (not found):
            errMsg = "Could not find baseUrl for account " + ds_account_id
    
    return {'ok': found, 'msg': errMsg} 

########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################



########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

def get_base_url(remove=1):
    # Dynamically get the url <remove> steps before this script's url
    script_url = get_script_url()
    parts = script_url.split("/")
    for x in range(0, remove):
        del parts[-1]
    url = '/'.join(map(str, parts))
    return url

def get_script_url():
    # Dynamically determine the script's url
    # For production use, this is not a great idea. Instead, set it
    # explicitly. Remember that for production, webhook urls must start with
    # https!
    my_url = rm_queryparameters(full_url(request.environ))
        # See http://flask.pocoo.org/docs/0.10/api/#flask.request
    return my_url

# See http://stackoverflow.com/a/8891890/64904
def url_origin(s, use_forwarded_host = False):
    ssl      = (('HTTPS' in s) and s['HTTPS'] == 'on')
    sp       = s['SERVER_PROTOCOL'].lower()
    protocol = sp[:sp.find('/')] + ('s' if ssl else '' )
    port     = s['SERVER_PORT']
    port     = '' if ((not ssl and port=='80') or (ssl and port=='443')) else (':' + port)
    host     = s['HTTP_X_FORWARDED_HOST'] if (use_forwarded_host and ('HTTP_X_FORWARDED_HOST' in s)) \
                 else (s['HTTP_HOST'] if ('HTTP_HOST' in s) else None)
    host     = host if (host != None) else (s['SERVER_NAME'] + port)
    return protocol + '://' + host

def full_url(s, use_forwarded_host = False):
    return url_origin(s, use_forwarded_host) + (s['REQUEST_URI'] if ('REQUEST_URI' in s) else s['PATH_INFO'])

def rm_queryparameters (input):
    parts = string.split(input, "?")
    return parts[0]

########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################    
    

## FIN ##

