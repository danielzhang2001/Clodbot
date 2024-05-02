"""
General Flask functions for the authorization process in accessing Google Sheets.
"""

import os
import psycopg2
import psycopg2.extras
import json
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
import pickle

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_KEY")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
REDIRECT = "https://clodbot.herokuapp.com/callback"


def get_config():
    # Returns the config settings.
    return {
        "web": {
            "client_id": os.getenv("CLIENT_ID"),
            "project_id": os.getenv("PROJECT_ID"),
            "auth_uri": os.getenv("AUTH_URI"),
            "token_uri": os.getenv("TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("AUTH_PROVIDER_X509_CERT_URL"),
            "client_secret": os.getenv("CLIENT_SECRET"),
            "redirect_uris": json.loads(os.getenv("REDIRECT_URIS")),
        }
    }


def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"), sslmode="require")


def store_credentials(server_id, creds):
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO credentials (server_id, data)
                VALUES (%s, %s)
                ON CONFLICT (server_id)
                DO UPDATE SET data = EXCLUDED.data;
                """,
                (server_id, psycopg2.extras.Binary(pickle.dumps(creds))),
            )
    conn.close()


def load_credentials(server_id):
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM credentials WHERE server_id = %s", (server_id,)
            )
            row = cur.fetchone()
    conn.close()
    if row:
        return pickle.loads(row[0])
    return None


@app.route("/authorize/<int:server_id>")
def authorize(server_id):
    # Handles authorization endpoint.
    client_config = get_config()
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT)
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    session["state"] = state
    session["server_id"] = server_id
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    # Handles callback endpoint.
    state = session.pop("state", None)
    server_id = session.pop("server_id", None)
    if not state or not server_id:
        return "Invalid state parameter or missing server_id", 400
    client_config = get_config()
    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, state=state, redirect_uri=REDIRECT
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    store_credentials(server_id, creds)
    return "Authentication successful! You can now close this page."


if __name__ == "__main__":
    app.run(debug=True)
