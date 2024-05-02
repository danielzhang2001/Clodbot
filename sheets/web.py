import os
from flask import Flask, request, redirect, session, url_for
from google_auth_oauthlib.flow import Flow
from sheets import *
import pickle
import json

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")

# Define the redirect URI used in your Flask application
FLASK_REDIRECT_URI = url_for("oauth2callback", _external=True)
print("Flask Redirect URI:", FLASK_REDIRECT_URI)


@app.route("/authorize")
def authorize():
    client_config = get_google_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
        redirect_uri=FLASK_REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    session["state"] = state
    return redirect(authorization_url)


@app.route("/oauth2callback")
def oauth2callback():
    state = session["state"]
    client_config = get_google_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
        state=state,
        redirect_uri=FLASK_REDIRECT_URI,
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)
    return "Authentication successful!"


if __name__ == "__main__":
    app.run(debug=True)
