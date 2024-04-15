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
                .get(spreadsheetId=sheets_id, range="Stats!B2:P285")
                .execute()
            )
            values = Update.filter_range(result.get("values", []))
            existing_names = set(cell for row in values for cell in row if cell)
            for name in player_names:
                if name not in existing_names:
                    col_letter, row_index = Update.next_cell(values)
                    next_cell = f"{col_letter}{row_index}"
                    update_range = f"Stats!{next_cell}"
                    body = {"values": [[name]]}
                    # service.spreadsheets().values().update(
                    #    spreadsheetId=sheets_id,
                    #    range=update_range,
                    #    valueInputOption="USER_ENTERED",
                    #    body=body,
                    # ).execute()
                    # row_adjusted_index = (row_index - 2) // 2
                    # if len(values) <= row_adjusted_index:
                    #    while len(values) < row_adjusted_index + 1:
                    #        values.append(["", "", "", ""])
                    # values[row_adjusted_index][
                    #    ["B", "D", "F", "H"].index(col_letter)
                    # ] = name
            return "Successfully updated the sheet with new player names."
        except HttpError as e:
            return f"Google Sheets API error: {e}"
        except Exception as e:
            return f"Failed to update the sheet: {e}"

    @staticmethod
    def next_cell(values):
        # Returns the row and column indices for the top of the next available section.
        column_letters = ["B", "F", "J", "N"]  # Maps to columns B, D, F, H for "Name"
        rows_per_block = 15  # Two rows to check, then skip 12 rows

        for block_start in range(
            0, len(values), rows_per_block
        ):  # Step through blocks of 14 rows
            # Ensure we have at least 2 rows to check in the current block
            if block_start + 1 >= len(values):
                continue  # Skip if the second row doesn't exist

            # Names are expected in the first row of the block
            names_row = values[block_start]
            print(f"NAMES ROW: {names_row}")
            # Details (Pokemon, Kills, Deaths) are in the second row of the block
            details_row = values[block_start + 1]

            # Iterate over each group position in the defined columns
            for col_idx, col_letter in enumerate(column_letters):
                # Calculate indices for details based on groups of 3 adjacent cells in the details row
                name_index = col_idx * 3
                details_start_idx = col_idx * 3
                # Collect all relevant cells for the group (Name + Pokemon, Kills, Deaths)
                group_cells = [
                    names_row[name_index] if len(names_row) > name_index else "",
                    (
                        details_row[details_start_idx]
                        if len(details_row) > details_start_idx
                        else ""
                    ),
                    (
                        details_row[details_start_idx + 1]
                        if len(details_row) > details_start_idx + 1
                        else ""
                    ),
                    (
                        details_row[details_start_idx + 2]
                        if len(details_row) > details_start_idx + 2
                        else ""
                    ),
                ]
                print(f"GROUP CELLS: {group_cells}")

                # Check if any required cell in the group is empty
                if any(cell == "" for cell in group_cells):
                    print(
                        f"Empty cell found in block starting at row {block_start + 1}, column {col_letter}"
                    )
                    return (
                        col_letter,
                        block_start + 2,
                    )  # Return the spreadsheet row number for "Name"

        return None  # Return None if no empty cell is found

    @staticmethod
    def filter_range(values):
        # Filters range of values to only relevant columns and rows.
        filtered_values = []
        for index, row in enumerate(values):
            batch_index = index // 15
            row_index = index % 15
            if row_index < 14:
                filtered_row = [
                    row[i] if len(row) > i else ""
                    for i in [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]
                ]
            filtered_values.append(filtered_row)
        return filtered_values
