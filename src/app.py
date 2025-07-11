import os
from flask import Flask, redirect, url_for, session, request, render_template_string
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]

app = Flask(__name__)
app.secret_key = os.urandom(24)

HOME_HTML = '''
<!DOCTYPE html>
<html>
<head><title>Home</title></head>
<body>
  <h2>Welcome to AgenticAIforAll</h2>
  {% if 'credentials' in session %}
    <p>Authenticated! <a href="/logout">Logout</a></p>
  {% else %}
    <a href="/login">Login with Google</a>
  {% endif %}
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HOME_HTML)

@app.route('/login')
def login():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    session['state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    flow.fetch_token(authorization_response=request.url)
    session['credentials'] = flow.credentials.to_json()
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('credentials', None)
    return redirect(url_for('home'))

@app.route('/contacts')
def contacts():
    if 'credentials' not in session:
        return redirect(url_for('login'))
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(eval(session['credentials']), SCOPES)
        service = build("people", version="v1", credentials=creds)
        results = (
            service.people()
            .connections()
            .list(
                resourceName="people/me",
                pageSize=10,
                personFields="names,emailAddresses",
            )
            .execute()
        )
        connections = results.get("connections", [])
        names = [person.get("names", [{}])[0].get("displayName", "No Name") for person in connections]
        return render_template_string('<h2>Your Contacts</h2><ul>{% for name in names %}<li>{{ name }}</li>{% endfor %}</ul><a href="/">Home</a>', names=names)
    except HttpError as err:
        return f"Error: {err}"

if __name__ == '__main__':
    app.run(debug=True)
