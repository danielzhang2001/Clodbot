"""
The function to list either all player names or Pokemon names from the Google Sheet.
"""

import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sheets.sheet import *
from errors import *


class List:
    @staticmethod
    async def list_data(creds: Credentials, sheet_link: str, data: str) -> str:
        # Lists all player names from the sheet.
        if not is_valid_sheet(sheet_link, creds):
            raise InvalidSheet(sheet_link)
        print("HERE?")
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        if data.lower() not in ("pokemon", "players"):
            raise NoList()
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        sheet_range = "Stats!B2:T285"
        for sheet in sheets:
            if sheet["properties"]["title"] == "Stats":
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            if data.lower() == "players":
                raise NoPlayers()
            elif data.lower() == "pokemon":
                raise NoPokemon()
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=sheet_range)
            .execute()
        )
        values = result.get("values", [])
        if data.lower() == "players":
            if not get_players(values):
                raise NoPlayers()
            return create_player_message(values)
        elif data.lower() == "pokemon":
            if not get_pokemon(values):
                raise NoPokemon()
            return create_pokemon_message(values)
