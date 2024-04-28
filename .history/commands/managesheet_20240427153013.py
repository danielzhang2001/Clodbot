"""
The functions to manage Google Sheets in association with Pokemon Showdown replay data. 
"""

import requests
import json
from discord.ext.commands import Context
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from showdown.replay import *
from sheets.sheet import *
from sheets.utils import *
from errors import *

default_link = load_links()


class ManageSheet:
    @staticmethod
    async def update_sheet(
        server_id: int, creds: Credentials, sheet_link: str, replay_link: str
    ) -> str:
        # Updates sheets with replay data.
        if not is_valid_sheet(creds, sheet_link):
            creds = await authenticate_sheet(server_id, force_login=True)
            if not is_valid_sheet(creds, sheet_link):
                raise InvalidSheet(sheet_link)
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        title = sheet_metadata["properties"]["title"]
        try:
            response = requests.get(replay_link + ".json")
            response.raise_for_status()
            json_data = json.loads(response.text)
        except requests.exceptions.RequestException:
            raise InvalidReplay(replay_link)
        stats = get_stats(json_data)
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
        for player_name, pokemon_data in stats.items():
            player_name = get_replay_players(json_data)[player_name]
            pokemon_data = [
                (pokemon, [data["kills"], data["deaths"]])
                for pokemon, data in pokemon_data.items()
            ]
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
        server_id: int, creds: Credentials, sheet_link: str, player_name: str
    ) -> str:
        # Deletes player section from the sheet.
        if not is_valid_sheet(creds, sheet_link):
            creds = await authenticate_sheet(server_id, force_login=True)
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
        players = [player[0] for player in get_sheet_players(values)]
        if player_name.lower() in [player.lower() for player in players]:
            player_name = next(
                (name for name in players if name.lower() == player_name.lower()),
                player_name,
            )
        else:
            raise NameDoesNotExist(player_name)
        section_range = f"Stats!{get_section_range(values, player_name)}"
        delete_data(service, spreadsheet_id, sheet_id, section_range)
        return f"**{player_name}** removed at [**{title}**]({sheet_link})."

    @staticmethod
    async def list_data(
        server_id: int, creds: Credentials, sheet_link: str, data: str
    ) -> str:
        # Lists all player names from the sheet.
        if not is_valid_sheet(creds, sheet_link):
            creds = await authenticate_sheet(server_id, force_login=True)
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
            if not get_sheet_players(values):
                raise NoPlayers()
            return create_player_message(values)
        elif data.lower() == "pokemon":
            if not get_sheet_pokemon(values):
                raise NoPokemon()
            return create_pokemon_message(values)

    @staticmethod
    async def set_default(
        ctx: Context, server_id: int, creds: Credentials, sheet_link: str
    ) -> str:
        # Sets the default sheet link.
        if not is_valid_sheet(creds, sheet_link):
            creds = await authenticate_sheet(server_id, force_login=True)
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
        default_link[server_id] = sheet_link
        save_links(default_link)
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
            server_id = ctx.guild.id if ctx.guild else 0
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
