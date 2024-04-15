"""
The function to give update Google Sheets with Pokemon Showdown replay information. 
"""

import os.path
import pickle
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from showdown.replay import *


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class Update:
    @staticmethod
    def authenticate_sheet():
        # Authenticates sheet functionality with appropriate credentials.
        creds = None
        token_path = os.path.join("sheets", "token.pickle")
        credentials_path = os.path.join("sheets", "credentials.json")
        if os.path.exists(token_path):
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)
        return creds

    @staticmethod
    async def update_sheet(creds, sheets_id, replay_link):
        # Updates sheets with replay data.
        service = build("sheets", "v4", credentials=creds)
        try:
            # Fetch the replay log data
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
            player_names = get_player_names(raw_data)
            player_names = [player_names["p1"], player_names["p2"]]
            player_names = " vs ".join(player_names)
            service = build("sheets", "v4", credentials=creds)
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=sheets_id).execute()
            )
            sheets = sheet_metadata.get("sheets", "")
            sheet_names = [sheet["properties"]["title"] for sheet in sheets]
            if "Stats" not in sheet_names:
                body = {"requests": [{"addSheet": {"properties": {"title": "Stats"}}}]}
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheets_id, body=body
                ).execute()
            values = [[player_names_value]]
            body = {"values": values}
            range_to_update = "Stats!A1"
            service.spreadsheets().values().update(
                spreadsheetId=sheets_id,
                range=range_to_update,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return "Update successful"
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"
