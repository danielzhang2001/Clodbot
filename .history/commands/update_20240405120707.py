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
            stats_sheet_exists = any(
                sheet["properties"]["title"] == "Stats" for sheet in sheets
            )
            if not stats_sheet_exists:
                body = {
                    "requests": [
                        {
                            "addSheet": {
                                "properties": {
                                    "title": "Stats",
                                    "gridProperties": {
                                        "rowCount": 1000,
                                        "columnCount": 26,
                                    },
                                }
                            }
                        }
                    ]
                }
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheets_id, body=body
                ).execute()
            range_name = "Stats!B2:H1000"
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheets_id, range=range_name)
                .execute()
            )
            values = result.get("values", [])
            column_letters = ["B", "D", "F", "H"]
            existing_names = [item for sublist in values for item in sublist if item]
            row_index, col_index = Update.next_cell(values, column_letters)
            for name in player_names:
                if name in existing_names:
                    continue
                while (
                    row_index <= len(values) and values[row_index - 2][col_index] != ""
                ):
                    col_index += 1
                    if col_index > 3:
                        col_index = 0
                        row_index += 2
                next_cell = f"{column_letters[col_index]}{row_index}"
                update_range = f"Stats!{next_cell}"
                body = {"values": [[name]]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheets_id,
                    range=update_range,
                    valueInputOption="USER_ENTERED",
                    body=body,
                ).execute()
                col_index += 1
                if col_index > 3:
                    col_index = 0
                    row_index += 2
            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"

    @staticmethod
    def next_cell(values, column_letters):
        # Returns the row and column indices for the next available cell.
        print(f"VALUES: {values}")
        row_index = 2
        col_index = 0
        found = False

        # Iterate over each row and each column within that row to find the first empty cell
        for r_idx, row in enumerate(values):
            # Checking each column within the current row
            for c_idx in range(4):  # We only have 4 columns to check: B, D, F, H
                # Determine if the current position is within the length of the row and is empty
                if len(row) > c_idx and row[c_idx] == "":
                    row_index = 2 + r_idx * 2
                    col_index = c_idx
                    found = True
                    break
                elif len(row) <= c_idx:
                    # If the row is shorter than needed, we can use this position
                    row_index = 2 + r_idx * 2
                    col_index = c_idx
                    found = True
                    break
            if found:
                break
        else:
            # If no empty cell found, place the next names in the next available row at the first position
            row_index = 2 + len(values) * 2  # Adjust to the next available row
            col_index = 0  # Start from the first column

        print(
            f"Next empty cell is at row {row_index} and column {column_letters[col_index]}"
        )
        return row_index, col_index
