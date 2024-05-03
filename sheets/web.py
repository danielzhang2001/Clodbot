"""
General Quart functions for the authorization process in accessing Google Sheets.
"""

import os
import pickle
import json
import aiopg
import asyncio
from quart import Quart, Response, redirect, session, request
from google_auth_oauthlib.flow import Flow
from google.auth.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, Dict

app = Quart(__name__)
app.secret_key = os.getenv("QUART_KEY")
app.config["PREFERRED_URL_SCHEME"] = "https"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
REDIRECT = "https://clodbot.herokuapp.com/callback"
DSN = os.getenv("DATABASE_URL")

pool = None


async def get_db_connection():
    global pool
    if pool is None:
        pool = await aiopg.create_pool(DSN)
    return pool


@app.before_serving
async def initialize_pool():
    global pool
    pool = await aiopg.create_pool(DSN)


def is_valid_creds(
    creds: Credentials,
    sheet_link: str,
) -> bool:
    # Checks if the creds is valid for the sheet.
    try:
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        service = build("sheets", "v4", credentials=creds)
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return True
    except (IndexError, HttpError):
        return False


def get_config() -> Dict[str, Dict[str, object]]:
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


async def store_credentials(server_id, creds) -> None:
    # Stores credentials into a database.
    pool = await get_db_connection()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO credentials (server_id, data)
                VALUES (%s, %s)
                ON CONFLICT (server_id)
                DO UPDATE SET data = EXCLUDED.data;
                """,
                (server_id, pickle.dumps(creds)),
            )
            await conn.commit()


async def load_credentials(server_id) -> Optional[Credentials]:
    # Loads existing credentials.
    pool = await get_db_connection()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT data FROM credentials WHERE server_id = %s", (server_id,)
            )
            row = await cur.fetchone()
    if row:
        return pickle.loads(row[0])
    return None


@app.route("/authorize/<int:server_id>/<path:sheet_link>")
async def authorize(server_id, sheet_link) -> Response:
    # Handles authorization endpoint.
    client_config = get_config()
    flow = Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT)
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    session["state"] = state
    session["server_id"] = server_id
    session["sheet_link"] = sheet_link
    return redirect(authorization_url)


@app.route("/callback")
async def callback() -> str:
    # Handles callback endpoint.
    state = session.pop("state", None)
    server_id = session.pop("server_id", None)
    sheet_link = session.pop("sheet_link", None)
    client_config = get_config()
    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, state=state, redirect_uri=REDIRECT
    )
    authorization_response = request.url.replace("http://", "https://")
    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials
    if creds and creds.valid and is_valid_creds(creds, sheet_link):
        await store_credentials(server_id, creds)
        return "Authentication successful! You can now close this page."
    else:
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO invalid_sheets (sheet_link) VALUES (%s) ON CONFLICT DO NOTHING;",
                    (sheet_link,),
                )
                await conn.commit()
        return (
            "You don't have permission to edit this sheet or the sheet doesn't exist."
        )


if __name__ == "__main__":
    app.run(debug=True)
