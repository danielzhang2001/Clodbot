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
    async def update_sheet(
        creds: Credentials, sheets_link: str, replay_link: str
    ) -> str:
        # Updates sheets with replay data.
        try:
            spreadsheet_id = sheets_link.split("/d/")[1].split("/")[0]
            service = build("sheets", "v4", credentials=creds)
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
            players = get_player_names(raw_data)
            pokes = get_pokes(raw_data)
            p1_count = get_p1_count(raw_data)
            nickname_mapping1, nickname_mapping2 = get_nickname_mappings(raw_data)
            stats = get_stats(
            raw_data, pokes, p1_count, nickname_mapping1, nickname_mapping2
        )
        formatted_stats = format_stats(players, stats)
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        sheet_range = "Stats!B2:T285"
        for sheet in sheets:
            if sheet["properties"]["title"] == "Stats":
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            body = {"requests": [{"addSheet": {"properties": {"title": "Stats"}}}]}
            sheet_response = (
                service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
            sheet_id = sheet_response["replies"][0]["addSheet"]["properties"]["sheetId"]
            color_background(service, spreadsheet_id, sheet_id)
        for player_data in formatted_stats:
            name = player_data[0]
            pokemon_data = player_data[1]
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
        return "Sheet updated."
