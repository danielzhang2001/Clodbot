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
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
            names_dict = get_player_names(raw_data)
            player_names = [names_dict["p1"], names_dict["p2"]]
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=sheets_id).execute()
            )
            sheets = sheet_metadata.get("sheets", "")
            sheet_exists = any(
                sheet["properties"]["title"] == "Stats" for sheet in sheets
            )
            if not sheet_exists:
                body = {"requests": [{"addSheet": {"properties": {"title": "Stats"}}}]}
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheets_id, body=body
                ).execute()
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheets_id, range="Stats!B2:H1000")
                .execute()
            )
            values = Update.filter_range(result.get("values", []))
            existing_names = set(cell for row in values for cell in row if cell)
            for name in player_names:
                if name not in existing_names:
                    col_letter, row_index = Update.next_cell(
                        values, ["B", "D", "F", "H"]
                    )
                    next_cell = f"{col_letter}{row_index}"
                    update_range = f"Stats!{next_cell}"
                    body = {"values": [[name]]}
                    service.spreadsheets().values().update(
                        spreadsheetId=sheets_id,
                        range=update_range,
                        valueInputOption="USER_ENTERED",
                        body=body,
                    ).execute()
                    row_adjusted_index = (row_index - 2) // 2
                    if len(values) <= row_adjusted_index:
                        while len(values) < row_adjusted_index + 1:
                            values.append(["", "", "", ""])
                    values[row_adjusted_index][
                        ["B", "D", "F", "H"].index(col_letter)
                    ] = name
            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"

    @staticmethod
    def next_cell(values, column_letters):
        # Returns the row and column indices for the next available cell.
        row_index = 2
        while True:
            current_row = values[row_index - 2] if (row_index - 2) < len(values) else []
            for col_index, letter in enumerate(column_letters):
                if len(current_row) <= col_index or current_row[col_index] == "":
                    return letter, row_index
            row_index += 2

    @staticmethod
    def filter_range(values):
        # Filters range of values to only relevant columns and rows.
        filtered_values = []
        included_rows = set()
        for row in values:
            filtered_row = [
                row[i] if len(row) > i else ""
                for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]
            ]
            filtered_values.append(filtered_row)
        return filtered_values
