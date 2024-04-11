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
        creds: Credentials, spreadsheet_id: str, replay_link: str
    ) -> str:
        # Updates sheets with replay data.
        service = build("sheets", "v4", credentials=creds)
        try:
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
            players = get_player_names(raw_data)
            pokes = get_pokes(raw_data)
            p1_count = get_p1_count(raw_data)
            nickname_mapping1, nickname_mapping2 = get_nickname_mappings(raw_data)
            stats = get_stats(
                raw_data,
                pokes,
                p1_count,
                nickname_mapping1,
                nickname_mapping2,
            )
            formatted_stats = format_stats(players, stats)
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            sheets = sheet_metadata.get("sheets", "")
            sheet_id = None
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
                sheet_id = sheet_response["replies"][0]["addSheet"]["properties"][
                    "sheetId"
                ]
            for player_data in formatted_stats:
                name = player_data[0]
                pokemon_data = player_data[1]
                result = (
                    service.spreadsheets()
                    .values()
                    .get(spreadsheetId=spreadsheet_id, range="Stats!B2:P285")
                    .execute()
                )
                values = result.get("values", [])
                if check_labels(values, name):
                    update_data(service, spreadsheet_id, "Stats!B2:P285", pokemon_data)
                else:
                    next_cell = next_cell(values)
                    update_cell = f"Stats!{next_cell}"
                    insert_data(
                        service, spreadsheet_id, update_cell, name, pokemon_data
                    )
                    col = next_cell[0]
                    row = int(next_cell[1:])
                    merge_cells(service, spreadsheet_id, sheet_id, col, row)
            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"


def find_pokemon_stats_range(values: List[List[str]], name: str) -> str:
    # Searches for the name and returns the 12x3 cell range for Pokemon stats as A1 notation if found.
    for row_index, row in enumerate(values):
        if name in row:
            name_index = row.index(name)
            # Check if the next row contains "Pokemon", "Kills", and "Deaths"
            if (
                row_index + 1 < len(values)
                and values[row_index + 1][name_index] == "Pokemon"
                and values[row_index + 1][name_index + 1] == "Kills"
                and values[row_index + 1][name_index + 2] == "Deaths"
            ):
                # Calculate the A1 notation range for the 12x3 stats sector
                start_col = chr(65 + name_index)  # Convert index to column letter
                end_col = chr(ord(start_col) + 2)  # Column for "Deaths"
                start_row = row_index + 3  # Skip the header and labels row
                end_row = start_row + 11  # 12 rows for the stats
                return f"{start_col}{start_row}:{end_col}{end_row}"
    return ""  # Return an empty string if the name and labels are not found
