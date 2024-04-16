"""
The function to remove a player name with all of their data from Google Sheets.
"""

"""
The function to update Google Sheets with Pokemon Showdown replay information. 
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
from sheets.sheet import *
from errors import *


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class Update:
    @staticmethod
    def authenticate_sheet() -> Credentials:
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
    async def remove_player(
        creds: Credentials, sheets_link: str, player_name: str
    ) -> str:
        # Removes player section from the sheet.
        try:
            spreadsheet_id = sheets_link.split("/d/")[1].split("/")[0]
        except IndexError:
            raise InvalidSheet(sheets_link)
        service = build("sheets", "v4", credentials=creds)
        try:
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
        except HttpError:
            raise InvalidSheet(sheets_link)
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        sheet_range = "Stats!B2:T285"
        for sheet in sheets:
            if sheet["properties"]["title"] == "Stats":
                sheet_id = sheet["properties"]["sheetId"]
                break
          result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=sheet_range)
                .execute()
            )
            values = result.get("values", [])
            if check_labels(values, name):
                stat_range = f"Stats!{get_range(values, name)}"
                update_data(service, spreadsheet_id, sheet_id, stat_range, pokemon_data)
            else:
                start_cell = f"Stats!{next_cell(values)}"
                add_data(
                    service, spreadsheet_id, sheet_id, start_cell, name, pokemon_data
                )
        return f"Sheet updated [**HERE**]({sheets_link})."
