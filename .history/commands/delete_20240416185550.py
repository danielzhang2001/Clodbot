"""
The function to delete a player name with all of their data from the Google Sheet.
"""

import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sheets.sheet import *
from errors import *


class Delete:
    @staticmethod
    async def delete_player(
        creds: Credentials, sheet_link: str, player_name: str
    ) -> str:
        # Deletes player section from the sheet.
        if not is_valid_sheet(sheet_link, creds):
            raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
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
            raise NameDoesNotExist(player_name)
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=sheet_range)
            .execute()
        )
        values = result.get("values", [])
        if player_name not in [player[0] for player in get_players(values)]:
            raise NameDoesNotExist(player_name)
        section_range = f"Stats!{get_section_range(values, player_name)}"
        delete_data(service, spreadsheet_id, sheet_id, section_range)
        return f"Player removed [**HERE**]({sheet_link})."
