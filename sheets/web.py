import os
import json
from google.oauth2 import service_account
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
import pickle

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")


def get_google_client_config():
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(os.getenv("CREDENTIALS"))
    )
    return {
        "installed": {
            "client_id": os.getenv("CLIENT_ID"),
            "project_id": os.getenv("PROJECT_ID"),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uris": json.loads(os.getenv("REDIRECT_URIS")),
        },
        "credentials": credentials,  # This may need to be passed separately depending on API usage
    }


# Rest of your Flask app
