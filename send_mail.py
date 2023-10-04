import json
import time
import requests
import threading

from flask import Flask
from flask import request
from flask import render_template
from bs4 import BeautifulSoup


app = Flask(__name__)


# Configure this.
FROM_EMAIL_ADDR = 'ihorkurylo5@zohomail.com'
TO_EMAIL_ADDR = 'andriilohvin@gmail.com'
REDIRECT_URL = 'http://95.164.44.248:5000/callback/'
CLIENT_ID = '1000.735XB81YY6IYR5Z8J84DTIMP9JTMLK'
CLIENT_SECRET = '2a86f1976f183e11cd98934a3a1a13ce2383cb1d4a'
BASE_OAUTH_API_URL = 'https://accounts.zoho.com/'
BASE_API_URL = 'https://mail.zoho.com/api/'


ZOHO_DATA = {
    "access_token": "",
    "refresh_token": "",
    "api_domain": "https://www.zohoapis.com",
    "token_type": "Bearer",
    "expires_in": 3600,
    "account_id": "",
    "folder_id": "",
}


def req_zoho():
    url = (
        "%soauth/v2/auth?"
        "scope=ZohoMail.accounts.READ,ZohoMail.messages.ALL,ZohoMail.folders.READ&"
        "client_id=%s&"
        "response_type=code&"
        "access_type=offline&"
        "redirect_uri=%s"
    ) % (BASE_OAUTH_API_URL, CLIENT_ID, REDIRECT_URL)
    print('CLICK THE LINK:')
    print(url)
    print('This only has to be done once.')


def get_access_token(code):
    state = request.args.get('state')
    url = '%soauth/v2/token' % BASE_OAUTH_API_URL
    data = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URL,
        'scope': 'ZohoMail.accounts.READ,ZohoMail.messages.ALL,ZohoMail.folders.READ',
        'grant_type': 'authorization_code',
        'state': state
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post(url, data=data, headers=headers)
    data = json.loads(r.text)
    print(data)
    ZOHO_DATA['access_token'] = data['access_token']


def get_account_id():
    url = BASE_API_URL + 'accounts'
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + ZOHO_DATA['access_token']
    }
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)
    ZOHO_DATA['account_id'] = data['data'][0]['accountId']


def send_mail(body, email_address):
    url = BASE_API_URL + 'accounts/%s/messages'
    url = url % ZOHO_DATA['account_id']
    data = {
        "fromAddress": FROM_EMAIL_ADDR,
        "toAddress": email_address,
        "ccAddress": "",
        "bccAddress": "",
        "subject": "Test E-Mail",
        "content": body,
        "askReceipt": "no"
    }
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + ZOHO_DATA['access_token']
    }
    r = requests.post(url, headers=headers, json=data)
    print(r.text)

def get_mail_context(folder_id, message_id, from_address, thread_id):
    url = (
        "%saccounts/%s/folders/%s/messages/%s/content?"
        "includeBlockContent=%s"
    ) % (BASE_API_URL, ZOHO_DATA['account_id'], folder_id, message_id, "true")
    
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + ZOHO_DATA['access_token']
    }
    
    print(url)
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)
    emails = data['data']['content']
    soup = BeautifulSoup(emails, 'html.parser')
    print(soup.get_text())
    filename = f"./data/message-{from_address}-{thread_id}.txt"
    with open("filename.txt", 'a') as f:
        f.write(filename + '\n')
    with open(filename, 'a') as f:
        f.write(emails + '\n')

# def get_mail_folders():
#     url = BASE_API_URL + 'accounts/%s/folders'
#     url = url % ZOHO_DATA['account_id']
#     headers = {
#         'Authorization': 'Zoho-oauthtoken ' + ZOHO_DATA['access_token']
#     }
#     r = requests.get(url, headers=headers)
#     data = json.loads(r.text)
#     print(data['data'][0]['folderId'], data['data'][0]['folderName'])
#     ZOHO_DATA['folder_id'] = data['data'][0]['folderId']  # 7666736000000008014

def get_mail_list(start):

    url = BASE_API_URL + 'accounts/%s/messages/view'
    url = url % ZOHO_DATA['account_id']
    url = (
        "%s?"
        "folderId=%s&"
        "start=%s&"
        "limit=%s"
    ) % (url, ZOHO_DATA['folder_id'], start, 200)
    
    headers = {
        'Authorization': 'Zoho-oauthtoken ' + ZOHO_DATA['access_token']
    }
    
    r = requests.get(url, headers=headers)
    data = json.loads(r.text)
    print(data)
    if len(data['data']) == 0:
        return False
    for message in data['data']:
        message_id = message['messageId']
        folder_id = message['folderId']
        from_address = message['fromAddress']
        thread_id = ""
        if 'threadId' in message:
            thread_id = message['threadId']
        get_mail_context(folder_id, message_id, from_address, thread_id)
    return True

def refresh_auth():
    # Update the access token every 50 minutes using the refresh token.
    # The access token is valid for exactly 1 hour.
    time.sleep(10)
    while True:
        url = (
            '%soauth/v2/token?'
            'refresh_token=%s&'
            'client_id=%s&'
            'client_secret=%s&'
            'grant_type=refresh_token'
        ) % (BASE_OAUTH_API_URL, ZOHO_DATA['refresh_token'], CLIENT_ID, CLIENT_SECRET)
        r = requests.post(url)
        data = json.loads(r.text)
        if 'access_token' in data:
            ZOHO_DATA['access_token'] = data['access_token']
            print('refreshed', ZOHO_DATA)
            time.sleep(3000)  # 50 minutes
        else:
            # Retry after 1 minute
            time.sleep(60)


@app.route('/callback/', methods=['GET', 'POST'])
def zoho_callback_route():
    print("here")
    code = request.args.get('code', None)
    print(code)
    if code is not None:
        get_access_token(code)
        get_account_id()
    for i in range(0, 20):
        if get_mail_list(1 + i*200) == False :
            break
    # get_mail_list()
    return 'OK', 200


@app.route('/sendmail/', methods=['GET', 'POST'])
def send_mail_route():
    # Send a HTML email!
    print("sent")
    data = ['1', '2', '3']
    mail = render_template('mail_template.j2', data=data)
    send_mail(mail, TO_EMAIL_ADDR)
    return 'OK', 200


@app.route('/getmail/', methods=['GET', 'POST'])
def get_mail_route():
    # Get all folders!
    print("get")
    get_mail_list()
    return 'OK', 200


def main():
    req_zoho()
    t = threading.Thread(target=refresh_auth)
    t.start()
    app.run(host='0.0.0.0')


if __name__ == '__main__':
    main()
