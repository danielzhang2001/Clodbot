import os
from flask import Flask, request, redirect, session, url_for
from google_auth_oauthlib.flow import Flow
import pickle
import json

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


def get_google_client_config():
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uris": json.loads(os.getenv("GOOGLE_REDIRECT_URIS")),
        }
    }


@app.route("/authorize")
def authorize():
    client_config = get_google_client_config()
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
        redirect_uri=url_for("oauth2callback", _external=True),
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
        redirect_uri=url_for("oauth2callback", _external=True),
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    with open("token.pickle", "wb") as token:
        pickle.dump(creds, token)
    return "Authentication successful!"


if __name__ == "__main__":
    app.run(debug=True)
