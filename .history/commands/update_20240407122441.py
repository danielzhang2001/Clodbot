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
                .get(spreadsheetId=sheets_id, range="Stats!B2:P285")
                .execute()
            )
            values = result.get("values", [])
            print(f"{values}")
            existing_names = set(cell for row in values for cell in row if cell)
            for name in player_names:
                if name not in existing_names:
                    update_range = f"Stats!{next_cell(values)}"
                    body = {"values": [[name]]}
                    service.spreadsheets().values().update(
                        spreadsheetId=sheets_id,
                        range=update_range,
                        valueInputOption="USER_ENTERED",
                        body=body,
                    ).execute()
                    merge_range = next_cell(values)[0] + str(
                        int(next_cell(values)[1:]) + 2
                    )
                    merge_body = {
                        "requests": [
                            {
                                "mergeCells": {
                                    "range": {
                                        "sheetId": sheets_id,
                                        "startRowIndex": int(cell_range[1:]) - 1,
                                        "endRowIndex": int(merge_range[1:]),
                                        "startColumnIndex": ord(cell_range[0])
                                        - ord("A"),
                                        "endColumnIndex": ord(cell_range[0])
                                        - ord("A")
                                        + 1,  # Keeps single column span
                                    },
                                    "mergeType": "MERGE_ALL",
                                }
                            },
                            {
                                "updateCells": {
                                    "range": {
                                        "sheetId": sheets_id,
                                        "startRowIndex": int(cell_range[1:]) - 1,
                                        "endRowIndex": int(merge_range[1:]),
                                        "startColumnIndex": ord(cell_range[0])
                                        - ord("A"),
                                        "endColumnIndex": ord(cell_range[0])
                                        - ord("A")
                                        + 1,
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