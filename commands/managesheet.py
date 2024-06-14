"""
The functions to manage Google Sheets in association with Pokemon Showdown replay data. 
"""

import requests
import json
import requests
from discord.ext import commands
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from showdown.replay import *
from sheets.sheet import *
from sheets.web import *
from errors import *


class ManageSheet:
    @staticmethod
    async def update_sheet(
        ctx: commands.Context,
        server_id: int,
        creds: Credentials,
        sheet_link: str,
        sheet_name: str,
        replay_link: str,
        name_dict: Dict[str, str],
        week: Optional[int] = None,
    ) -> str:
        # Updates sheets with replay data.
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheet_title = sheet_metadata["properties"]["title"]
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
            if sheet["properties"]["title"] == sheet_name:
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
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
        if week is not None and not week_exists(
            service, spreadsheet_id, sheet_name, week
        ):
            add_week(service, spreadsheet_id, sheet_id, sheet_name, week)
        for player_name, pokemon_data in stats.items():
            player_name = get_replay_players(json_data)[player_name]
            if player_name in name_dict:
                player_name = name_dict[player_name]
            pokemon_data = [
                (pokemon, [data["kills"], data["deaths"]])
                for pokemon, data in pokemon_data.items()
            ]
            values = get_values(service, spreadsheet_id, f"{sheet_name}!B2:T285")
            if week is not None:
                add_columns(service, spreadsheet_id, sheet_id, week, values)
                start_cell = f"{sheet_name}!{next_week_cell(values, week)}"
                print(f"NEXT WEEK CELL FOR {player_name} IS: {start_cell}")
                add_data(
                    service,
                    spreadsheet_id,
                    sheet_id,
                    start_cell,
                    player_name,
                    pokemon_data,
                )
            else:
                if check_labels(values, player_name):
                    stat_range = f"{sheet_name}!{get_stat_range(values, player_name)}"
                    update_data(
                        service, spreadsheet_id, stat_range, player_name, pokemon_data
                    )
                else:
                    start_cell = f"{sheet_name}!{next_data_cell(values)}"
                    add_data(
                        service,
                        spreadsheet_id,
                        sheet_id,
                        start_cell,
                        player_name,
                        pokemon_data,
                        week,
                    )
        return f"Sheet updated at [**{sheet_title}**]({sheet_link}) using **{sheet_name}**."

    @staticmethod
    async def delete_player(
        ctx: commands.Context,
        server_id: int,
        creds: Credentials,
        sheet_link: str,
        sheet_name: str,
        player_name: str,
    ) -> str:
        # Deletes player section from the sheet.
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheet_title = sheet_metadata["properties"]["title"]
        sheets = sheet_metadata.get("sheets", "")
        sheet_id = None
        for sheet in sheets:
            if sheet["properties"]["title"] == sheet_name:
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            raise NameDoesNotExist(player_name, sheet_title, sheet_name)
        sheet_link = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
        values = get_values(service, spreadsheet_id, f"{sheet_name}!B2:T285")
        players = [player[0] for player in get_sheet_players(values)]
        if player_name.lower() in [player.lower() for player in players]:
            player_name = next(
                (name for name in players if name.lower() == player_name.lower()),
                player_name,
            )
        else:
            raise NameDoesNotExist(player_name, sheet_title, sheet_name)
        section_range = f"{sheet_name}!{get_section_range(values, player_name)}"
        delete_data(service, spreadsheet_id, sheet_id, section_range)
        return f"**{player_name}** removed at [**{sheet_title}**]({sheet_link}) using **{sheet_name}**."

    @staticmethod
    async def list_data(
        ctx: commands.Context,
        server_id: int,
        creds: Credentials,
        sheet_link: str,
        sheet_name: str,
        data: str,
    ) -> str:
        # Lists all player names from the sheet.
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
            if sheet["properties"]["title"] == sheet_name:
                sheet_id = sheet["properties"]["sheetId"]
                break
        if sheet_id is None:
            if data.lower() == "players":
                raise NoPlayers()
            elif data.lower() == "pokemon":
                raise NoPokemon()
        values = get_values(service, spreadsheet_id, f"{sheet_name}!B2:T285")
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
        server_id: int, creds: Credentials, sheet_link: str, sheet_name: str
    ) -> str:
        # Sets the default link for the server.
        if not sheet_name:
            sheet_name = "Stats"
        service = build("sheets", "v4", credentials=creds)
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheet_title = sheet_metadata["properties"]["title"]
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("BEGIN;")
                try:
                    await cur.execute(
                        """
                        INSERT INTO default_links (server_id, sheet_link, sheet_title, sheet_name)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (server_id)
                        DO UPDATE SET sheet_link = EXCLUDED.sheet_link, sheet_title = EXCLUDED.sheet_title, sheet_name = EXCLUDED.sheet_name;
                        """,
                        (server_id, sheet_link, sheet_title, sheet_name),
                    )
                    await cur.execute("COMMIT;")
                except Exception as e:
                    await cur.execute("ROLLBACK;")
                    raise e
        return f"Default sheet link set at [**{sheet_title}**]({sheet_link}) using **{sheet_name}**."

    @staticmethod
    async def get_default(server_id: int) -> str:
        # Returns the server's current default link.
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT sheet_link, sheet_title, sheet_name FROM default_links WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                sheet_link, sheet_title, sheet_name = row
        return f"Current default sheet at [**{sheet_title}**]({sheet_link}) using **{sheet_name}**."

    @staticmethod
    async def has_default(server_id: int) -> bool:
        # Returns whether the default link for the server exists or not.
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT EXISTS (SELECT 1 FROM default_links WHERE server_id = %s)",
                    (server_id,),
                )
                exists = await cur.fetchone()
        return bool(exists[0])

    @staticmethod
    async def use_default(server_id: int) -> str:
        # Returns the current default link and sheet name.
        pool = await get_db_connection()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT sheet_link, sheet_name FROM default_links WHERE server_id = %s",
                    (server_id,),
                )
                row = await cur.fetchone()
                return (row[0], row[1])
