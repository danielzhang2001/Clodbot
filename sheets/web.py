import os
import json
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import pickle

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")


def get_google_client_config():
    creds_json = json.loads(os.getenv("CREDENTIALS"))
    return {
        "web": {
            "client_id": os.getenv("CLIENT_ID"),
            "project_id": os.getenv("PROJECT_ID"),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uris": json.loads(os.getenv("REDIRECT_URIS")),
        },
        "credentials": service_account.Credentials.from_service_account_info(
            creds_json
        ),
    }


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
FLASK_REDIRECT_URI = "https://clodbot.herokuapp.com/callback"


@app.route("/authorize/<server_id>")
def authorize(server_id):
    print(f"Starting authorization for server_id: {server_id}")
    client_config = get_google_client_config()
    credentials = client_config["credentials"]
    flow = Flow.from_client_config(
        client_config["web"],
        scopes=SCOPES,
        redirect_uri=FLASK_REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    session["state"] = state
    session["server_id"] = server_id
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    state = session.pop("state", None)
    server_id = session.pop("server_id", None)
    if not state or not server_id:
        return "Invalid state parameter or missing server_id", 400

    client_config = get_google_client_config()
    credentials = client_config["credentials"]
    flow = Flow.from_client_config(
        client_config["installed"],
        scopes=SCOPES,
        state=state,
        redirect_uri=FLASK_REDIRECT_URI,
        credentials=credentials,
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials

    creds_directory = "sheets"
    if not os.path.exists(creds_directory):
        os.makedirs(creds_directory)
    token_filename = f"token_{server_id}.pickle"
    token_path = os.path.join(creds_directory, token_filename)
    with open(token_path, "wb") as token:
        pickle.dump(creds, token)

    return "Authentication successful! You can now close this page."


if __name__ == "__main__":
    app.run(debug=True)
