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

            # Ensure "Stats" sheet exists
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

            # Flatten the list for easier checking and determine filled cells
            filled_cells = [
                cell for row in values for cell in row if cell
            ]  # Non-empty cells
            next_available_index = len(
                filled_cells
            )  # Next available index based on filled cells

            column_letters = ["B", "D", "F", "H"]
            for name in player_names:
                if name in filled_cells:  # Skip if name is already listed
                    continue

                # Calculate row and column based on next available index
                row_number = 2 + next_available_index // 4
                column_letter = column_letters[next_available_index % 4]
                next_cell = f"{column_letter}{row_number}"

                # Update the sheet with the new name if not already listed
                update_range = f"Stats!{next_cell}"
                body = {"values": [[name]]}
                service.spreadsheets().values().update(
                    spreadsheetId=sheets_id,
                    range=update_range,
                    valueInputOption="USER_ENTERED",
                    body=body,
                ).execute()

                filled_cells.append(name)  # Update filled cells list
                next_available_index += 1  # Increment for next name

            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"
