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
    async def update_sheet(creds: Credentials, sheets_id: str, replay_link: str) -> str:
        # Updates sheets with replay data.
        service = build("sheets", "v4", credentials=creds)
        try:
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
            players = get_player_names(raw_data)
            pokes = get_pokes(raw_data)
            p1_count = get_p1_count(raw_data)
            nickname_mapping_player1, nickname_mapping_player2 = get_nickname_mappings(
                raw_data
            )
            stats = get_stats(
                raw_data,
                pokes,
                p1_count,
                nickname_mapping_player1,
                nickname_mapping_player2,
            )
            formatted_stats = format_stats(players, stats)
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=sheets_id).execute()
            )
            sheets = sheet_metadata.get("sheets", "")
            stats_sheet_id = None
            for sheet in sheets:
                if sheet["properties"]["title"] == "Stats":
                    stats_sheet_id = sheet["properties"]["sheetId"]
                    break
            if stats_sheet_id is None:
                body = {"requests": [{"addSheet": {"properties": {"title": "Stats"}}}]}
                add_sheet_response = (
                    service.spreadsheets()
                    .batchUpdate(spreadsheetId=sheets_id, body=body)
                    .execute()
                )
                stats_sheet_id = add_sheet_response["replies"][0]["addSheet"][
                    "properties"
                ]["sheetId"]
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=sheets_id, range="Stats!B2:P285")
                .execute()
            )
            values = result.get("values", [])
            for player_data in formatted_stats:
                player_name = player_data[0]
                pokemon = player_data[1]
                if player_name not in values:
                    cell_range = next_cell(values)
                    update_range = f"Stats!{cell_range}"
                    data_to_insert = (
                        [[player_name]]
                        + [["Pokemon", "Kills", "Deaths"]]
                        + [[poke[0], poke[1], poke[2]] for poke in pokemon]
                    )
                    print(f"{data_to_insert}")
                    body = {"values": data_to_insert}
                    service.spreadsheets().values().update(
                        spreadsheetId=sheets_id,
                        range=update_range,
                        valueInputOption="USER_ENTERED",
                        body=body,
                    ).execute()
                col = cell_range[0]
                row = int(cell_range[1:])
                merge_body = {
                    "requests": [
                        {
                            "mergeCells": {
                                "range": {
                                    "sheetId": stats_sheet_id,
                                    "startRowIndex": row - 1,
                                    "endRowIndex": row,
                                    "startColumnIndex": ord(col) - ord("A"),
                                    "endColumnIndex": ord(col) - ord("A") + 3,
                                },
                                "mergeType": "MERGE_ALL",
                            }
                        },
                        {
                            "repeatCell": {
                                "range": {
                                    "sheetId": stats_sheet_id,
                                    "startRowIndex": row - 1,
                                    "endRowIndex": row,
                                    "startColumnIndex": ord(col) - ord("A"),
                                    "endColumnIndex": ord(col) - ord("A") + 1,
                                },
                                "cell": {
                                    "userEnteredFormat": {
                                        "horizontalAlignment": "CENTER"
                                    }
                                },
                                "fields": "userEnteredFormat.horizontalAlignment",
                            }
                        },
                    ]
                }
                service.spreadsheets().batchUpdate(
                    spreadsheetId=sheets_id,
                    body=merge_body,
                ).execute()
            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"