"""
The function to manage Google Sheets in association with Pokemon Showdown replay data. 
"""

import requests
from discord.ext.commands import Context
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from showdown.replay import *
from sheets.sheet import *
from errors import *

default_link = {}


class ManageSheet:
    @staticmethod
    async def update_sheet(
        creds: Credentials, sheet_link: str, replay_link: str
    ) -> str:
        # Updates sheets with replay data.
        if not is_valid_sheet(creds, sheet_link):
            creds = authenticate_sheet(force_login=True)
            if not is_valid_sheet(creds, sheet_link):
                raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        title = sheet_metadata["properties"]["title"]
        try:
            response = requests.get(replay_link + ".log")
            response.raise_for_status()
            raw_data = response.text
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        players = get_player_names(raw_data)
        pokes = get_pokes(raw_data)
        p1_count = get_p1_count(raw_data)
        nickname_mapping1, nickname_mapping2 = get_nickname_mappings(raw_data)
        stats = get_stats(
            raw_data, pokes, p1_count, nickname_mapping1, nickname_mapping2
        )
        formatted_stats = format_stats(players, stats)
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
            sheet_id = sheet_response["replies"][0]["addSheet"]["properties"]["sheetId"]
            color_background(service, spreadsheet_id, sheet_id)
        sheet_link = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
            if sheet_id
            else sheet_link
        )
        for player_data in formatted_stats:
            player_name = player_data[0]
            pokemon_data = player_data[1]
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range="Stats!B2:T285")
                .execute()
            )
            values = result.get("values", [])
            if check_labels(values, player_name):
                stat_range = f"Stats!{get_stat_range(values, player_name)}"
                update_data(service, spreadsheet_id, sheet_id, stat_range, pokemon_data)
            else:
                start_cell = f"Stats!{next_cell(values)}"
                add_data(
                    service,
                    spreadsheet_id,
                    sheet_id,
                    start_cell,
                    player_name,
                    pokemon_data,
                )
        return f"Sheet updated at [**{title}**]({sheet_link})."

    @staticmethod
    async def delete_player(
        creds: Credentials, sheet_link: str, player_name: str
    ) -> str:
        # Deletes player section from the sheet.
        if not is_valid_sheet(creds, sheet_link):
            creds = authenticate_sheet(force_login=True)
            if not is_valid_sheet(creds, sheet_link):
                raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        title = sheet_metadata["properties"]["title"]
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        for sheet in sheets:
            if sheet["properties"]["title"] == "Stats":
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            raise NameDoesNotExist(player_name)
        sheet_link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="Stats!B2:T285")
            .execute()
        )
        values = result.get("values", [])
        players = get_players(values)
        player_names = [player[0] for player in players]
        if player_name.lower() in [player[0].lower() for player in get_players(values)]:
            player_name = player[0]
        else:
            raise NameDoesNotExist(player_name)
        section_range = f"Stats!{get_section_range(values, player_name)}"
        delete_data(service, spreadsheet_id, sheet_id, section_range)
        return f"**{player_name}** removed at [**{title}**]({sheet_link})."

    @staticmethod
    async def list_data(creds: Credentials, sheet_link: str, data: str) -> str:
        # Lists all player names from the sheet.
        if not is_valid_sheet(creds, sheet_link):
            creds = authenticate_sheet(force_login=True)
            if not is_valid_sheet(creds, sheet_link):
                raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        if data.lower() not in ("pokemon", "players"):
            raise NoList()
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
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
            .get(spreadsheetId=spreadsheet_id, range="Stats!B2:T285")
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

    @staticmethod
    def set_default(ctx: Context, creds: Credentials, sheet_link: str) -> str:
        # Sets the default sheet link.
        if not is_valid_sheet(creds, sheet_link):
            creds = authenticate_sheet(force_login=True)
            if not is_valid_sheet(creds, sheet_link):
                raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        title = sheet_metadata["properties"]["title"]
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        for sheet in sheets:
            if sheet["properties"]["title"] == "Stats":
                sheet_id = sheet["properties"]["sheetId"]
                break
        sheet_link = (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
            if sheet_id
            else sheet_link
        )
        server_id = ctx.guild.id if ctx.guild else 0
        default_link[server_id] = sheet_link
        return f"Default sheet link set at [**{title}**]({sheet_link})."

    @staticmethod
    def get_default(ctx: Context) -> str:
        # Retrieves the default sheet link.
        server_id = ctx.guild.id if ctx.guild else 0
        return default_link.get(server_id)

    @staticmethod
    def has_default(ctx: Context) -> bool:
        # Checks if a default sheet link is set.
        server_id = ctx.guild.id if ctx.guild else 0
        return server_id in default_link

    @staticmethod
    def display_default(ctx: Context, creds: Credentials) -> bool:
        # Displays the current default link.
        if ManageSheet.has_default(ctx):
            service = build("sheets", "v4", credentials=creds)
            spreadsheet_id = ManageSheet.get_default(ctx).split("/d/")[1].split("/")[0]
            sheet_metadata = (
                service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            )
            title = sheet_metadata["properties"]["title"]
            sheets = sheet_metadata.get("sheets", "")
            sheet_id = None
            for sheet in sheets:
                if sheet["properties"]["title"] == "Stats":
                    sheet_id = sheet["properties"]["sheetId"]
                    break
            sheet_link = (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
                if sheet_id
                else ManageSheet.get_default(ctx)
            )
            return f"Current default sheet at [**{title}**]({sheet_link})."
        else:
            raise NoDefault()
