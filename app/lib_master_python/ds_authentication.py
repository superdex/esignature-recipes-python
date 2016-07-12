# Python Authentication for DocuSign Recipes

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')

import json, certifi, requests, os, base64, math, string, urllib, random, time, re, hashlib, base64
from flask import request, session
# See http:#requests.readthedocs.org/ for information on the requests library
# See https:#urllib3.readthedocs.org/en/latest/security.html for info on making secure https calls
# in particular, run pip install certifi periodically to pull in the latest cert bundle

# Global constants
ds_account_id = None # If you're looking for a specific account_id, set this var
ds_legacy_login_url = "https://demo.docusign.net/restapi/v2/login_information" # change for production
ds_legacy_revokeOAuthToken_uri = "/oauth2/revoke"
oauth_authentication_server = "https://account-d.docusign.com/" # change for production
oauth_start = oauth_authentication_server + "/oauth/auth"
oauth_token = oauth_authentication_server + "/oauth/token"
oauth_userInfo = oauth_authentication_server + "/oauth/userinfo"
oauth_base_url_fragment = "/restapi/v2/accounts/" # Used to create base_url from base_uri
ca_bundle = "app/static/assets_master/ca-bundle.crt"
oauth_scope = "signature"



########################################################################
########################################################################
########################################################################
########################################################################
########################################################################
########################################################################

# We're storing authentication in the Flask session which is
# stored in a server-side file. See app/lib_master_python/json_session_interface
#
# In production, the OAuth client_id (the integration_key) and related
# information would be constants for the application. Here we're enabling them to be set
# at runtime (stored in the session) so the recipes can be easily tried out.
#
# Info stored in the session:
# auth: {authenticated: true/false
#        user_name
#        email
#        type: {oauth_code, legacy_oauth, ds_legacy}
#        account_id
#        base_url           # Used for API calls
#        auth_header_key    # Used for API calls
#        auth_header_value  # Used for API calls
#        client_id (integration_key)  # temp storage during authentication
#        client_secret # temp storage during authentication
#        oauth_state # temp storage during authentication
#        refresh_token # OAuth code grant only

def get_auth_status():
    """Returns the authentication status of the current session

    Returns a dictionary:
    auth_status = {
        authenticated: true/false,
        description: string. Eg "Authenticated as John Doe <john@doe.com> for account 12345"
            or "Not authenticated"
        }
    """
    auth_status = {}
    translator = {"oauth_code": "OAuth Authorization Code Grant",
                  "legacy_oauth": "Legacy OAuth Authentication",
                  "ds_legacy": "DocuSign Legacy Authentication"}

    if 'auth' in session:
        auth = session['auth']
    else:
        auth = {'authenticated': False}

    auth_status['authenticated'] = auth['authenticated']
    auth_status['auth'] = auth
    if auth['authenticated']:
        auth_status['description'] = 'Authenticated via {} as {} &lt;{}&gt; for the {} account ({})'.format(
            translator[auth['type']], auth['user_name'], auth['email'], auth['account_name'], auth['account_id'])
    else:
        auth_status['description'] = "You are not authenticated. Please choose an authentication method and submit the information:"

    return auth_status

def set_auth():
    """Enables the authentication to be set for the session.

    The Request body:
    type: {oauth_code, legacy_oauth, ds_legacy}

    code_client_id
    code_secret_key
    code_redirect_uri

    pw_client_id # For Legacy OAuth Password authentication. We start with the same as for DS Legacy
    pw_email
    pw_pw

    legacy_client_id: # same as integration_key. Required.
    legacy_email, # only supply if type == ds_legacy
    legacy_pw # only supply if type == ds_legacy

    The Response:
    {redirect: string, # If not False, then redirect the user's browser to this address to
                       # continue the auth process
     auth_status: same as from get_auth_status
     err: if not false then it contains the error message
    """

    req = request.get_json()
    delete_auth()
    if req["type"] == "ds_legacy":
        err = set_auth_ds_legacy(req)
        return {"err": err, "redirect": False, "auth_status": get_auth_status()}

    if req["type"] == "legacy_oauth":
        err = set_auth_legacy_oauth(req)
        return {"err": err, "redirect": False, "auth_status": get_auth_status()}

    if req["type"] == "oauth_code":
        r = set_auth_oauth_code(req)
        return {"err": r["err"], "redirect": r["redirect"], "auth_status": get_auth_status()}

def set_auth_ds_legacy(req):
    """Authenticate the user using legacy technique

    Side-effect: Sets Session["auth"]
    Returns err
    """

    # Normally, the client_id (Integration_key) is a constant for the app.
    auth_header_key = 'X-DocuSign-Authentication'
    auth_header_dict = {"Username": req["legacy_email"], "Password": req["legacy_pw"], "IntegratorKey": req["legacy_client_id"]}
    auth_header_value = json.dumps(auth_header_dict)
    r = authentication_login(auth_header_key, auth_header_value) # r is {err, account_id, base_url}

    if r["err"]:
        return r["err"]

    # Set Session["auth"]
    session["auth"] = {"authenticated": True,
        "user_name": r["user_name"],
        "email": r["email"],
        "type": req["type"],
        "account_id": r["account_id"],
        "account_name": r["account_name"],
        "base_url": r["base_url"],
        "auth_header_key": auth_header_key,
        "auth_header_value": auth_header_value}
    return False

def set_auth_legacy_oauth(req):
    """Authenticate the user using legacy OAuth technique

    Side-effect: Sets Session["auth"]
    Returns err
    """

    # Normally, the client_id (Integration_key) is a constant for the app.
    email = req["pw_email"]
    pw = req["pw_pw"]
    client_id = req["pw_client_id"]
    auth_header_key = 'X-DocuSign-Authentication'
    auth_header_dict = {"Username": email, "Password": pw, "IntegratorKey": client_id}
    auth_header_value = json.dumps(auth_header_dict)

    r = authentication_legacy_oauth_login(auth_header_key, auth_header_value) # r is {err, account_id, base_url}
    if r["err"]:
        return r["err"]

    # Set auth with intermediate credentials (Legacy Authentication)
    auth = {"authenticated": True,
            "user_name": r["user_name"],
            "email": r["email"],
            "type": req["type"],
            "account_id": r["account_id"],
            "account_name": r["account_name"],
            "base_url": r["base_url"],
            "auth_header_key": r["auth_header_key"],
            "auth_header_value": r["auth_header_value"]}

    # Set Session["auth"]
    session["auth"] = auth
    return False

def set_auth_oauth_code(req):
    """Start OAuth Authorization Code Grant process

    Store the Client ID and Secret in the session for later use when exchanging the code for a token

    Returns {err, redirect} where err is False or an error message
    """

    # Normally, the client_id (Integration_key), secret_key, and redirect_uri values are constants for the app.
    client_id = req["code_client_id"]
    secret_key = req["code_secret_key"]
    redirect_uri = req["code_redirect_uri"]

    if not client_id:
        return {"err": "Please include the Client ID (Integration Key)", "redirect": False}
    if not secret_key:
        return {"err": "Please include the Secret Key", "redirect": False}
    if not redirect_uri:
        return {"err": "Please include the Redirect URI", "redirect": False}

    # See https://developers.google.com/identity/protocols/OpenIDConnect#createxsrftoken
    oauth_state = hashlib.sha256(os.urandom(1024)).hexdigest()

    # Save info for later use
    session["auth"] = {"authenticated": False,
                       "type": req["type"],
                       "client_id": client_id,
                       "secret_key": secret_key,
                       "oauth_state": oauth_state}

    redirect = (oauth_start +
        "?response_type=code" +
        "&scope=" + oauth_scope +
        "&client_id=" + client_id +
        "&state=" + oauth_state +
        "&redirect_uri=" + redirect_uri)

    return {"err": False, "redirect": redirect}

def authentication_login(auth_header_key, auth_header_value):
    """Call the Authentication: login method, which is only used for legacy authentication

    Returns {err, account_id, base_url, user_name, email}
    """
    ds_headers = {'Accept': 'application/json'}
    ds_headers[auth_header_key] = auth_header_value
    err = False

    try:
        r = requests.get(ds_legacy_login_url, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign login: " + e
        return {'err': err}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign login, status is: " + r.content + " (" + str(status) + ")"})

    # get the baseUrl and accountId from the response body
    response = r.json()
    # Example response:
    # { "loginAccounts": [
    #       { "name": "DocuSign",   # account_name
    #         "accountId": "1374267",
    #         "baseUrl": "https://demo.docusign.net/restapi/v2/accounts/1374267",
    #         "isDefault": "true",
    #         "userName": "Recipe Login",
    #         "userId": "d43a4a6a-dbe7-491e-9bad-8f7b4cb7b1b5",
    #         "email": "temp2+recipe@kluger.com",
    #         "siteDescription": ""
    #      }
    # ]}
    #

    account_id = None
    found = False
    user_name = None
    email = None
    # Get account_id and base_url.
    if (ds_account_id == None):
        # Get default
        for account in response["loginAccounts"]:
            if (account["isDefault"] == "true"):
                account_id = account["accountId"]
                account_name =account["name"]
                base_url = account["baseUrl"]
                user_name = account["userName"]
                email = account["email"]
                found = True
                break

        if (not found):
            err = "Could not find default account for the username."
    else:
        # get the account's base_url
        for account in response["loginAccounts"]:
            if (account["accountId"] == ds_account_id):
                base_url = account["baseUrl"]
                user_name = account["userName"]
                email = account["email"]
                account_id = ds_account_id
                account_name =account["name"]
                found = True
                break
        if (not found):
            err = "Could not find baseUrl for account " + ds_account_id

    return {'err': err, 'account_id': account_id, 'base_url' : base_url,
            "user_name": user_name, "email": email, "account_name": account_name}

def authentication_legacy_oauth_login(auth_header_key, auth_header_value):
    """Obtains a legacy OAuth token by calling Authentication: login method with api_password true

    This authentication technique is currently the best choice for "Service Intergrations"

    This function is the same as the authentication_login except that
    query parameter api_password is used, and the response includes an OAuth token

    Returns {err, account_id, base_url, user_name, email, auth_header_key, auth_header_value}
    """
    ds_headers = {'Accept': 'application/json'}
    ds_headers[auth_header_key] = auth_header_value
    err = False

    try:
        r = requests.get(ds_legacy_login_url + "?api_password=true", headers=ds_headers)
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign login: " + e
        return {'err': err}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign login, status is: " + r.content + " (" + str(status) + ")"})

    # get the baseUrl and accountId from the response body
    response = r.json()
    # Example response:
    # { "apiPassword": "{PASSWORD}",
    #   "loginAccounts": [
    #       { "name": "DocuSign",   # account_name
    #         "accountId": "1374267",
    #         "baseUrl": "https://demo.docusign.net/restapi/v2/accounts/1374267",
    #         "isDefault": "true",
    #         "userName": "Recipe Login",
    #         "userId": "d43a4a6a-dbe7-491e-9bad-8f7b4cb7b1b5",
    #         "email": "temp2+recipe@kluger.com",
    #         "siteDescription": ""
    #      }
    # ]}
    #

    account_id = None
    found = False
    user_name = None
    email = None
    # Get account_id and base_url.
    if (ds_account_id == None):
        # Get default
        for account in response["loginAccounts"]:
            if (account["isDefault"] == "true"):
                account_id = account["accountId"]
                account_name = account["name"]
                base_url = account["baseUrl"]
                user_name = account["userName"]
                email = account["email"]
                found = True
                break

        if (not found):
            err = "Could not find default account for the username."
    else:
        # get the account's base_url
        for account in response["loginAccounts"]:
            if (account["accountId"] == ds_account_id):
                base_url = account["baseUrl"]
                user_name = account["userName"]
                email = account["email"]
                account_id = ds_account_id
                account_name = account["name"]
                found = True
                break
        if (not found):
            err = "Could not find baseUrl for account " + ds_account_id

    auth_header_key = "Authorization"
    auth_header_value = "Bearer " + response["apiPassword"]
    return {'err': err, 'account_id': account_id, 'base_url': base_url,
            "user_name": user_name, "email": email, "account_name": account_name,
            "auth_header_key": auth_header_key, "auth_header_value": auth_header_value}

def auth_token_delete():
    """Deletes the authentication token on DocuSign

    Returns {err} -- False or an error message
    """
    if 'auth' in session:
        auth = session['auth']
        if not auth["authenticated"]:
            return {"err": "Please authenticate with DocuSign."}
    else:
        return {"err": "Please authenticate with DocuSign."}

    if auth['type'] == "legacy_oauth":
        # Currently, we can only delete legacy_oauth tokens
        return authentication_legacy_oauth_revoke(auth)
    else:
        return {"err": "Authentication type is {}. This method requires Legacy OAuth authentication".format(auth['type'])}

def authentication_legacy_oauth_revoke(auth):
    """Revoke a Legacy OAuth token by calling Authentication: revokeOAuthToken method

    See https://docs.docusign.com/esign/restapi/Authentication/Authentication/revokeOAuthToken/

    Returns {err} False, or an error message
    """
    # The url is /v2/oauth2/revoke NB, it does NOT include an account number!
    # The base url includes the account_id. Eg "https://demo.docusign.net/restapi/v2/accounts/1374267"
    # We need to peel off the accounts/1374267 part so we can call the OAuth token endpoint.
    url = rm_url_parts(auth["base_url"], 2) + ds_legacy_revokeOAuthToken_uri
    ds_headers = {'Accept': 'application/json', auth["auth_header_key"]: auth["auth_header_value"]}
    data = {}

    try:
        r = requests.post(url, headers=ds_headers, json=data)
    except requests.exceptions.RequestException as e:
        return {'err': "Error calling Authentication:revokeOAuthToken " + str(e)}

    status = r.status_code
    if (status != 200):
        return ({'err': "Error calling DocuSign Authentication:revokeOAuthToken<br/>Status is: " +
                        str(status) + ". Response: <pre><code>" + r.text + "</code></pre>"})

    return {'err': False}

########################################################################
########################################################################

def rm_url_parts (url, remove):
    """Dynamically get the url <remove> steps before the original url"""

    parts = url.split("/")
    for x in range(0, remove):
        del parts[-1]
    url = '/'.join(map(str, parts))
    return url

########################################################################
########################################################################

def delete_auth():
    """Delete the session's authentication information"""
    session["auth"] = {"authenticated": False}
    return {"err": False}

########################################################################
########################################################################

def auth_redirect():
    """Process the incoming data from OAuth Authorization Code Grant redirect"""

    # An unsuccessful authentication redirect (User chose to not grant access)
    # error=access_denied&error_message=The%20user%20did%20not%20consent%20to%20connecting%20the%20application.&state=c611e8268536e1218f24f6991f1abd1a3c23cbbe6787887afc3138aede2f1840
    # Success:
    # code=eyJ0eXAiOi_blah_blah_P6BwFtw&state=70a5333877c3f57bcdc407a7776c747290f95ce8ec1ff5203d6af35e9d5b36e3

    # First check that the state is correct. This is important to prevent CSRF attacks. See http://goo.gl/av06hU
    # In this example, the user is notified of the behavior.
    # You might also want to alert an administrator or two. Or log all of the request's information

    if 'auth' in session and 'oauth_state' in session['auth']:
        auth = session['auth']
    else:
        return "No authentication information in the session! Possible CSRF attack!"

    oauth_state = auth['oauth_state']
    incoming_state = request.args.get('state')
    if incoming_state != oauth_state:
        return "Authentication state information mismatch! Possible CSRF attack!"

    incoming_error_message = request.args.get('error_message')
    if incoming_error_message:
        return incoming_error_message

    incoming_code = request.args.get('code')
    if not incoming_code:
        return "Code was not supplied by server! Please contact your administrator."

    # Exchange the code for tokens
    err = oauth_token_for_code(auth, incoming_code)
    if err:
        return err

    # Get the User Info
    err = get_oauth_user_info()
    return err  # If no errors, then redirect to home page. The user is now authenticated!

def oauth_token_for_code(auth, code):
    """Calls the authentication server to get the tokens in return for the code

    Returns err (an error message) or False to indicate no problems
    """
    client_secret = auth["client_id"] + ':' + auth["secret_key"]
    client_secret_b64 = base64.b64encode(client_secret)

    try:
        r = requests.post(oauth_token,
                headers={'Authorization': "Basic " + client_secret_b64},
                data={'grant_type': 'authorization_code', 'code': code})
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign for OAuth token: " + e
        return err

    status = r.status_code
    if (status != 200):
        extra = "Tip: check that your secret key is correct."
        return "Error calling DocuSign for OAuth token: " + r.content + " (" + str(status) + "). " + extra

    # we should now have the following in r.json() --
    # access_token	The token you will use in the Authorization header of calls to the DocuSign API.
    # token_type	This is the kind of token. It is usually Bearer
    # refresh_token	A token you can use to get a new access_token without requiring user interaction.
    # expires_in	The number of seconds before the access_token expires.
    #
    # Example content: {"access_token":"[587 characters]","token_type":"Bearer","refresh_token":"[587 characters]","expires_in":28800,"user_api":null}

    token_info = r.json()

    # Save in the session.
    auth['access_token'] = token_info["access_token"]
    auth['refresh_token'] = token_info["refresh_token"]
    auth['token_type'] = token_info["token_type"]
    auth["auth_header_key"] = "Authorization"
    auth["auth_header_value"] = auth['token_type'] + " " + auth['access_token']

    # We no longer need the client ID or secret for this user's session
    # Normally, these values are associated with the app, not with an
    # individual session
    auth["client_id"] = False
    auth["secret_key"] = False

    # Save info
    session["auth"] = auth
    return False

def get_oauth_user_info():
    """Call the OAuth: userInfo method, which is only used for OAuth authentication

    Returns err
    Side-effect: Sets session["auth"]
    """

    auth = session["auth"]
    ds_headers = {'Accept': 'application/json'}
    ds_headers[auth["auth_header_key"]] = auth["auth_header_value"]
    err = False

    try:
        r = requests.get(oauth_userInfo, headers=ds_headers)
    except requests.exceptions.RequestException as e:
        err = "Error calling DocuSign login: " + e
        return err

    status = r.status_code
    if (status != 200):
        return "Error calling DocuSign OAuth userInfo: " + r.content + " (" + str(status) + ")"

    # get info from the response body
    response = r.json()
    # Example response:
    # {
    #     "sub": "50d89ab1-dad5-4a0a-b410-92ee3110b970",
    #     "accounts": [
    #         {
    #          "account_id": "e783eff5-53e1-45b2-b599-3810e89c2aac",
    #          "is_default": true,
    #          "account_name": "NewCo",
    #          "base_uri": "https://demo.docusign.net"
    #          }
    #     ],
    #     "name": "Dev User",
    #     "given_name": "Dev",
    #     "family_name": "User",
    #     "email": "dev.user@docusign.com"
    # }

    account_id = None
    found = False
    user_name = response["name"]
    email = response["email"]
    # Get account_id and base_url.
    if (ds_account_id == None):
        # Get default
        for account in response["accounts"]:
            if account["is_default"]:
                account_id = account["account_id"]
                account_name = account["account_name"]
                base_uri = account["base_uri"]
                found = True
                break

        if (not found):
            return "Could not find default account for " + user_name
    else:
        # get the account's base_url
        for account in response["accounts"]:
            if (account["account_id"] == ds_account_id):
                base_uri = account["base_uri"]
                account_id = ds_account_id
                account_name = account["account_name"]
                found = True
                break
        if (not found):
            return "Could not find baseUrl for account " + ds_account_id

    # Add to Auth and store
    auth["authenticated"] = True
    auth["user_name"] = user_name
    auth["email"] = email
    auth["account_id"] = account_id
    auth["account_name"] = account_name
    auth["base_url"] = base_uri + oauth_base_url_fragment + account_id

    session["auth"] = auth

########################################################################
########################################################################
########################################################################


## FIN ##

