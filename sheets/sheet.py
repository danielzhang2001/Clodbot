"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""

import pickle
import json
import asyncio
import aiopg
import os.path
from discord.ext import commands
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict, Tuple
from sheets.web import *
from errors import *


async def authenticate_sheet(
    ctx: commands.Context, server_id: int, sheet_link: str
) -> Credentials:
    # Authenticates sheet functionality with appropriate credentials.
    creds = await load_credentials(server_id)
    if creds and creds.valid and is_valid_creds(creds, sheet_link):
        return creds
    auth_url = f"https://clodbot.herokuapp.com/authorize/{server_id}/{sheet_link}"
    await ctx.send(f"Please authenticate [**HERE**]({auth_url}).")
    while True:
        await asyncio.sleep(10)
        is_invalid = await check_sheets(sheet_link)
        if is_invalid:
            await clear_sheets(sheet_link)
            return AuthFailure()
        creds = await load_credentials(server_id)
        if creds and creds.valid and is_valid_creds(creds, sheet_link):
            return creds


async def check_sheets(sheet_link):
    # Checks invalid_sheets database if there exists an entry.
    pool = await get_db_connection()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM invalid_sheets WHERE sheet_link = %s", (sheet_link,)
            )
            result = await cur.fetchone()
            return result is not None


async def clear_sheets(sheet_link):
    # Clears invalid_sheets database.
    pool = await get_db_connection()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("BEGIN;")
            try:
                await cur.execute(
                    "DELETE FROM invalid_sheets WHERE sheet_link = %s", (sheet_link,)
                )
                await cur.execute("COMMIT;")
            except Exception as e:
                await cur.execute("ROLLBACK;")
                raise e


def letter_to_index(column: str) -> int:
    # Converts a column letter to its associated index value.
    index = 0
    for char in column:
        index = index * 26 + (ord(char.upper()) - ord("A")) + 1
    return index - 1


def week_exists(
    service: Resource, spreadsheet_id: str, sheet_name: str, week: int
) -> bool:
    # Checks to see if the specific week section is empty or not.
    cell_range = f"{sheet_name}!{next_week_range(week)}"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=cell_range, majorDimension="ROWS")
        .execute()
    )
    values = result.get("values", [])
    if values and values[0] and values[0][0] == f"Week {week}":
        return True
    return False


def any_week_exists(service: Resource, spreadsheet_id: str, sheet_name: str) -> bool:
    # Checks if any week exists in the sheet.
    week = 1
    while True:
        if week_exists(service, spreadsheet_id, sheet_name, week):
            return True
        cell_range = f"{sheet_name}!{next_week_range(week)}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=cell_range, majorDimension="ROWS")
            .execute()
        )
        values = result.get("values", [])
        if not values:
            break
        week += 1
    return False


def any_data_exists(service: Resource, spreadsheet_id: str, sheet_name: str) -> bool:
    # Checks if any non-week data exists in the sheet.
    letters = ["B", "G", "L", "Q"]
    section = 1
    while True:
        cell_range = f"{sheet_name}!B{section + 1}:Q{section + 2}"
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=cell_range, majorDimension="ROWS")
            .execute()
        )
        values = result.get("values", [])
        if not values:
            break
        names_row = values[0] if len(values) > 0 else []
        details_row = values[1] if len(values) > 1 else []
        for index, letter in enumerate(letters):
            start_index = index * 5
            group_cells = [
                (
                    names_row[start_index]
                    if len(names_row) > start_index and names_row[start_index] != ""
                    else "Empty"
                ),
                (
                    details_row[start_index]
                    if len(details_row) > start_index
                    and details_row[start_index] == "POKEMON"
                    else "Empty"
                ),
                (
                    details_row[start_index + 1]
                    if len(details_row) > start_index + 1
                    and details_row[start_index + 1] == "GAMES"
                    else "Empty"
                ),
                (
                    details_row[start_index + 2]
                    if len(details_row) > start_index + 2
                    and details_row[start_index + 2] == "KILLS"
                    else "Empty"
                ),
                (
                    details_row[start_index + 3]
                    if len(details_row) > start_index + 3
                    and details_row[start_index + 3] == "DEATHS"
                    else "Empty"
                ),
            ]
            if all(cell != "Empty" for cell in group_cells):
                return True
        section += 15
    return False


def add_week(
    service: Resource, spreadsheet_id: str, sheet_id: int, sheet_name: str, week: int
) -> None:
    # Adds the week into the sheet on the specific cell, as well as does cell formatting.
    cell_range = f"{sheet_name}!{next_week_range(week)}"
    data = f"Week {week}"
    body = {"values": [[data]]}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=cell_range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    widen_columns(service, spreadsheet_id, sheet_id)
    clear_cells(service, spreadsheet_id, sheet_id, cell_range)
    format_week(service, spreadsheet_id, sheet_id, cell_range)


def add_data(
    service: Resource,
    spreadsheet_id: str,
    sheet_id: int,
    cell: str,
    player_name: str,
    pokemon: List[Tuple[str, List[int]]],
) -> None:
    # Adds the Player Name, Pokemon, Games, Kills and Deaths data into the sheet on the specific cell, as well as does cell formatting.
    sheet_name, start_cell = cell.split("!")
    col, row = start_cell.rstrip("0123456789"), int(
        "".join(filter(str.isdigit, start_cell))
    )
    num_rows = max(12, len(pokemon))
    col_index = 0
    for char in col:
        col_index = col_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = col_index + 3
    end_col = ""
    while end_index > 0:
        end_index -= 1
        end_col = chr(end_index % 26 + ord("A")) + end_col
        end_index //= 26
    cell_range = f"{sheet_name}!{col}{row}:{end_col}{row + num_rows + 1}"
    data = (
        [[player_name], ["POKEMON", "GAMES", "KILLS", "DEATHS"]]
        + [[poke[0], 1] + poke[1] for poke in pokemon]
        + [[" "] * 4] * max(0, 12 - len(pokemon))
    )
    body = {"values": data}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=cell,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    widen_columns(service, spreadsheet_id, sheet_id)
    clear_cells(service, spreadsheet_id, sheet_id, cell_range)
    format_data(service, spreadsheet_id, sheet_id, cell_range)


def delete_data(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Deletes all of the data for the player section.
    widen_columns(service, spreadsheet_id, sheet_id)
    clear_cells(service, spreadsheet_id, sheet_id, cell_range)
    clear_text(service, spreadsheet_id, sheet_id, cell_range)


def update_data(
    service: Resource,
    spreadsheet_id: str,
    cell_range: str,
    player_name: str,
    pokemon_data: List[Tuple[str, List[int]]],
) -> None:
    # Updates the Pokemon, Games, Kills and Deaths data into the sheet.
    values = get_range_values(service, spreadsheet_id, cell_range)
    sheet_name = cell_range.split("!")[0]
    start_cell = cell_range.split("!")[1].split(":")[0]
    end_cell = cell_range.split("!")[1].split(":")[1]
    start_col = "".join(filter(str.isalpha, start_cell))
    start_row = int("".join(filter(str.isdigit, start_cell)))
    end_col = "".join(filter(str.isalpha, end_cell))
    end_row = int("".join(filter(str.isdigit, end_cell)))
    pokemon_indices = {
        row[0].strip(): start_row + idx
        for idx, row in enumerate(values)
        if row and row[0].strip()
    }
    for pokemon_name, stats in pokemon_data:
        if pokemon_name in pokemon_indices:
            row_index = pokemon_indices[pokemon_name]
            row_range = f"{sheet_name}!{start_col}{row_index}:{end_col}{row_index}"
            update_pokemon(
                service,
                spreadsheet_id,
                row_range,
                stats,
            )

    for pokemon_name, stats in pokemon_data:
        if pokemon_name not in pokemon_indices:
            values = get_range_values(service, spreadsheet_id, cell_range)
            if not values:
                empty_row_index = 4
            else:
                try:
                    empty_row_index = next(
                        start_row + idx
                        for idx, row in enumerate(values)
                        if not row or not row[0].strip()
                    )
                except StopIteration:
                    if len(values) < 12:
                        empty_row_index = start_row + len(values)
                    else:
                        raise FullSection(player_name, pokemon_name)
            empty_row_range = (
                f"{sheet_name}!{start_col}{empty_row_index}:{end_col}{empty_row_index}"
            )
            add_pokemon(
                service,
                spreadsheet_id,
                empty_row_range,
                pokemon_name,
                stats,
            )


def add_pokemon(
    service: Resource,
    spreadsheet_id: str,
    row_range: str,
    pokemon_name: str,
    stats: List[int],
) -> None:
    # Adds new Pokemon entries to the appropriate section in the sheet.
    values = {"values": [[pokemon_name, 1, stats[0], stats[1]]]}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=row_range,
        body=values,
        valueInputOption="USER_ENTERED",
    ).execute()


def update_pokemon(
    service: Resource, spreadsheet_id: str, row_range: str, stats: List[int]
) -> None:
    # Updates existing Pokemon entries to the appropriate section in the sheet.
    values = get_range_values(service, spreadsheet_id, row_range)
    updated_values = [
        [
            values[0][0],
            str(int(values[0][1]) + 1),
            str(int(values[0][2]) + stats[0]),
            str(int(values[0][3]) + stats[1]),
        ]
    ]
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=row_range,
        body={"values": updated_values},
        valueInputOption="USER_ENTERED",
    ).execute()


def create_player_message(values: List[List[str]]) -> str:
    # Creates the message when asked to list players in the sheet.
    players = sorted(get_sheet_players(values), key=lambda x: (-int(x[1]), int(x[2])))
    message = "**PLAYERS:**\n```"
    message += "\n".join(
        [
            f"{i+1}) {name} (Kills: {kills}, Deaths: {deaths})"
            for i, (name, kills, deaths) in enumerate(players)
        ]
    )
    message += "\n```"
    return message


def create_pokemon_message(values: List[List[str]]) -> str:
    # Creates the message when asked to list Pokemon in the sheet.
    pokemon = sorted(
        get_sheet_pokemon(values),
        key=lambda x: (
            (x[2] == "N/A", -int(x[2]) if x[2] not in ("", "N/A") else 0),
            (x[3] == "N/A", int(x[3]) if x[3] not in ("", "N/A") else 0),
        ),
    )
    message = "**POKEMON:**\n```"
    message += "\n".join(
        [
            f"{i+1}) {player}'s {name} (Kills: {kills}, Deaths: {deaths})"
            for i, (player, name, kills, deaths) in enumerate(pokemon)
        ]
    )
    message += "\n```"
    return message


def format_week(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Formats all of the cells and text for the week section.
    merge_cells(service, spreadsheet_id, sheet_id, cell_range)
    outline_cells(service, spreadsheet_id, sheet_id, cell_range)
    color_week(service, spreadsheet_id, sheet_id, cell_range)
    style_week(service, spreadsheet_id, sheet_id, cell_range)
    center_text(service, spreadsheet_id, sheet_id, cell_range)


def format_data(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Formats all of the cells and text for the player data section.
    start_cell, end_cell = cell_range.split("!")[1].split(":")
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_letter = ""
    temp_index = start_index
    while temp_index > 0:
        temp_index -= 1
        start_letter = chr(temp_index % 26 + ord("A")) + start_letter
        temp_index //= 26
    end_letter = ""
    temp_index = end_index
    while temp_index > 0:
        temp_index -= 1
        end_letter = chr(temp_index % 26 + ord("A")) + end_letter
        temp_index //= 26
    sheet_name = cell_range.split("!")[0]
    start_row = int("".join(filter(str.isdigit, start_cell)))
    end_row = int("".join(filter(str.isdigit, end_cell)))
    name_range = f"{sheet_name}!{start_letter}{start_row}:{end_letter}{start_row}"
    header_range = f"{sheet_name}!{start_letter}{start_row}:{end_letter}{start_row + 1}"
    merge_cells(service, spreadsheet_id, sheet_id, name_range)
    outline_cells(service, spreadsheet_id, sheet_id, cell_range)
    color_data(service, spreadsheet_id, sheet_id, cell_range)
    style_data(service, spreadsheet_id, sheet_id, cell_range)
    center_text(service, spreadsheet_id, sheet_id, header_range)


def add_columns(
    service: Resource,
    spreadsheet_id: str,
    sheet_id: int,
    week: int,
    values: List[List[str]],
) -> None:
    # Adds the specified number of columns needed if the end of the sheet is reached.
    range_str = next_week_range(week)
    start_row = int(range_str.split("B")[1].split(":")[0])
    end_row = int(range_str.split(":B")[1])
    rightmost_col = len(values[0]) - 1
    filled_col = -1
    for col in range(rightmost_col, -1, -1):
        has_value = False
        for row in range(start_row - 1, end_row):
            if row < len(values) and col < len(values[row]) and values[row][col] != "":
                filled_col = col
                has_value = True
                break
        if has_value:
            break
    new_col = 5 - (rightmost_col - filled_col)
    if new_col > 0:
        requests = [
            {
                "appendDimension": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "length": new_col,
                }
            }
        ]
        body = {"requests": requests}
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()


def widen_columns(service: Resource, spreadsheet_id: str, sheet_id: int) -> None:
    # Widens certain columns on the sheet.
    columns = [
        {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 5},
        {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 6, "endIndex": 10},
        {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 11, "endIndex": 15},
        {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": 16, "endIndex": 20},
    ]
    requests = [
        {
            "updateDimensionProperties": {
                "range": column,
                "properties": {"pixelSize": 120},
                "fields": "pixelSize",
            }
        }
        for column in columns
    ]
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def merge_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Merges the cells in the range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    body = {
        "requests": [
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index,
                    },
                    "mergeType": "MERGE_ALL",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def outline_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Bolds and colors the outline of all the cells in the range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    body = {
        "requests": [
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index,
                    },
                    "top": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                    "bottom": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                    "left": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                    "right": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                    "innerHorizontal": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                    "innerVertical": {
                        "style": "SOLID",
                        "width": 1,
                        "color": {"red": 0.69, "green": 0.69, "blue": 0.69},
                    },
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def color_week(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the cells in the range for week.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    if (start_row - 2) // 15 % 2 == 0:
        color = {"red": 0, "green": 0, "blue": 0}
    else:
        color = {"red": 0, "green": 0.23, "blue": 0.47}
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "cell": {"userEnteredFormat": {"backgroundColor": color}},
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def color_data(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the cells in the range for player data.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    body = {
        "requests": [
            {
                "addBanding": {
                    "bandedRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_index,
                            "endColumnIndex": end_index,
                        },
                        "rowProperties": {
                            "headerColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0,
                            },
                            "firstBandColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0,
                            },
                            "secondBandColor": {
                                "red": 0,
                                "green": 0.23,
                                "blue": 0.47,
                            },
                        },
                    }
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def color_background(service: Resource, spreadsheet_id: str, sheet_id: int) -> None:
    # Colors the entire sheet.
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1000,
                        "startColumnIndex": 0,
                        "endColumnIndex": 26,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": {
                                "red": 0.21,
                                "green": 0.21,
                                "blue": 0.21,
                            }
                        }
                    },
                    "fields": "userEnteredFormat.backgroundColor",
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def clear_cells(service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str):
    # Clears all formatting in the range.
    banding_ids = get_bandings(service, spreadsheet_id, sheet_id, cell_range)
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = 0
    for char in "".join(filter(str.isalpha, start_cell)):
        start_col = start_col * 26 + (ord(char.upper()) - ord("A")) + 1
    start_col -= 1
    end_col = 0
    for char in "".join(filter(str.isalpha, end_cell)):
        end_col = end_col * 26 + (ord(char.upper()) - ord("A")) + 1
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 0.21, "green": 0.21, "blue": 0.21},
                        "textFormat": {
                            "foregroundColor": None,
                            "fontSize": 10,
                            "bold": False,
                            "italic": False,
                            "strikethrough": False,
                            "underline": False,
                        },
                        "horizontalAlignment": "LEFT",
                        "verticalAlignment": "BOTTOM",
                        "wrapStrategy": "OVERFLOW_CELL",
                        "borders": None,
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy,borders)",
            }
        }
    ]
    result = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, includeGridData=False)
        .execute()
    )
    sheets = result.get("sheets", [])
    sheet = next(
        (
            s
            for s in sheets
            if "properties" in s
            and "sheetId" in s["properties"]
            and s["properties"]["sheetId"] == sheet_id
        ),
        None,
    )
    if not sheet:
        return
    banded_ranges = sheet.get("bandedRanges", [])
    for banding_id in banding_ids:
        banding = next(br for br in banded_ranges if br["bandedRangeId"] == banding_id)
        brange = banding.get("range", {})
        brange_start_row = brange.get("startRowIndex", float("inf"))
        brange_end_row = brange.get("endRowIndex", 0)
        brange_start_col = brange.get("startColumnIndex", float("inf"))
        brange_end_col = brange.get("endColumnIndex", 0)
        if (
            start_row == brange_start_row
            and end_row == brange_end_row
            and start_col == brange_start_col
            and end_col == brange_end_col
        ):
            requests.append({"deleteBanding": {"bandedRangeId": banding_id}})
        else:
            if start_row > brange_start_row:
                requests.append(
                    {
                        "updateBanding": {
                            "bandedRange": {
                                "bandedRangeId": banding_id,
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": brange_start_row,
                                    "endRowIndex": start_row,
                                    "startColumnIndex": brange_start_col,
                                    "endColumnIndex": brange_end_col,
                                },
                            },
                            "fields": "range",
                        }
                    }
                )
            if end_row < brange_end_row:
                requests.append(
                    {
                        "updateBanding": {
                            "bandedRange": {
                                "bandedRangeId": banding_id,
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": end_row,
                                    "endRowIndex": brange_end_row,
                                    "startColumnIndex": brange_start_col,
                                    "endColumnIndex": brange_end_col,
                                },
                            },
                            "fields": "range",
                        }
                    }
                )
            if start_col > brange_start_col:
                requests.append(
                    {
                        "updateBanding": {
                            "bandedRange": {
                                "bandedRangeId": banding_id,
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": brange_start_row,
                                    "endRowIndex": brange_end_row,
                                    "startColumnIndex": brange_start_col,
                                    "endColumnIndex": start_col,
                                },
                            },
                            "fields": "range",
                        }
                    }
                )
            if end_col < brange_end_col:
                requests.append(
                    {
                        "updateBanding": {
                            "bandedRange": {
                                "bandedRangeId": banding_id,
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": brange_start_row,
                                    "endRowIndex": brange_end_row,
                                    "startColumnIndex": end_col + 1,
                                    "endColumnIndex": brange_end_col,
                                },
                            },
                            "fields": "range",
                        }
                    }
                )
            if brange_start_col < start_col:
                requests.append(
                    {
                        "updateBanding": {
                            "bandedRange": {
                                "bandedRangeId": banding_id,
                                "range": {
                                    "sheetId": sheet_id,
                                    "startRowIndex": brange_start_row,
                                    "endRowIndex": brange_end_row,
                                    "startColumnIndex": brange_start_col,
                                    "endColumnIndex": start_col - 1,
                                },
                            },
                            "fields": "range",
                        }
                    }
                )
    body = {"requests": requests}
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def clear_text(service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str):
    # Clears all text in the range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    body = {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index,
                    },
                    "fields": "userEnteredValue",
                    "rows": [
                        {
                            "values": [
                                {"userEnteredValue": {}}
                                for _ in range(start_index, end_index)
                            ]
                        }
                        for _ in range(start_row, end_row)
                    ],
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def style_week(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the text in the range for week and sets the font and font size.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "fontFamily": "Acme",
                                "fontSize": 24,
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat",
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def style_data(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the text in the range for player data and sets the font and font size.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat": {
                                "fontFamily": "Acme",
                                "fontSize": 10,
                                "foregroundColor": {
                                    "red": 1.0,
                                    "green": 1.0,
                                    "blue": 1.0,
                                },
                            }
                        }
                    },
                    "fields": "userEnteredFormat.textFormat",
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def center_text(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Centers all the text in the given cell range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    body = {
        "requests": [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment": "MIDDLE",
                        }
                    },
                    "fields": "userEnteredFormat(horizontalAlignment,verticalAlignment)",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()


def get_bandings(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> List[int]:
    # Returns the IDs of overlapping bandings.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = "".join(filter(str.isalpha, start_cell))
    end_col = "".join(filter(str.isalpha, end_cell))
    start_index = 0
    for char in start_col:
        start_index = start_index * 26 + (ord(char.upper()) - ord("A")) + 1
    end_index = 0
    for char in end_col:
        end_index = end_index * 26 + (ord(char.upper()) - ord("A")) + 1
    start_index -= 1
    result = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, includeGridData=False)
        .execute()
    )
    sheets = result.get("sheets", [])
    sheet = next(
        (
            s
            for s in sheets
            if "properties" in s
            and "sheetId" in s["properties"]
            and s["properties"]["sheetId"] == sheet_id
        ),
        None,
    )
    if not sheet:
        return []
    banded_ranges = sheet.get("bandedRanges", [])
    overlapping_ids = []
    for banded_range in banded_ranges:
        brange = banded_range.get("range", {})
        if (
            brange.get("sheetId") == sheet_id
            and "sheetId" in brange
            and not (
                brange.get("endRowIndex", 0) <= start_row
                or brange.get("startRowIndex", float("inf")) >= end_row
                or brange.get("endColumnIndex", 0) <= start_index
                or brange.get("startColumnIndex", float("inf")) >= end_index
            )
        ):
            overlapping_ids.append(banded_range["bandedRangeId"])
    return overlapping_ids


def get_sheet_players(values: List[List[str]]) -> List[List[str]]:
    # Returns a list of all the player names and their total kills/deaths.
    players = []
    if not values or len(values) < 3:
        return players
    for i in range(1, len(values), 15):
        header_row = values[i]
        for index, name in enumerate(header_row):
            if name.strip() == "":
                continue
            if i + 1 >= len(values) or values[i + 1][index].strip() == "":
                continue
            total_kills = 0
            total_deaths = 0
            for j in range(i + 2, min(i + 14, len(values))):
                if index < len(values[j]):
                    data_row = values[j]
                    if len(data_row) > index + 3:
                        kills = data_row[index + 2]
                        deaths = data_row[index + 3]
                        total_kills += int(kills) if kills.isdigit() else 0
                        total_deaths += int(deaths) if deaths.isdigit() else 0
            players.append([name, total_kills, total_deaths])
    return players


def get_sheet_pokemon(values: List[List[str]]) -> List[List[str]]:
    # Returns a list of all the Pokemon names with their player and their total kills/deaths.
    pokemon = []
    for i in range(3, len(values), 15):
        for j in range(i, min(i + 12, len(values))):
            row = values[j]
            for idx, value in enumerate(row):
                if value.strip() and not (
                    value.strip().replace(".", "", 1).isdigit()
                    and value.strip().count(".") <= 1
                ):
                    player = None
                    for k in range(j - 1, 0, -1):
                        if idx < len(values[k]) and "POKEMON" in values[k][idx]:
                            player = values[k - 1][idx].strip() if k > 0 else None
                            break
                        else:
                            continue
                    if player:
                        kills = (
                            row[idx + 2].strip()
                            if idx + 2 < len(row) and row[idx + 2].strip().isdigit()
                            else "N/A"
                        )
                        deaths = (
                            row[idx + 3].strip()
                            if idx + 3 < len(row) and row[idx + 3].strip().isdigit()
                            else "N/A"
                        )
                        pokemon.append([player, value.strip(), kills, deaths])
    return pokemon


def get_stat_range(values: List[List[str]], name: str) -> str:
    # Searches for the name and returns the range of the section with Pokemon stats associated with that name.
    name_lower = name.lower()
    for row_index, row in enumerate(values):
        row_lower = [cell.lower() for cell in row]
        if name_lower in row_lower:
            name_index = row_lower.index(name_lower)
            start_col = chr(65 + name_index)
            end_col = chr(ord(start_col) + 3)
            start_row = row_index + 3
            end_row = start_row + 11
            return f"{start_col}{start_row}:{end_col}{end_row}"
    return None


def get_section_range(values: List[List[str]], player_name: str) -> str:
    # Searches for the name and returns the range of the entire section for that name.
    for row_index, row in enumerate(values):
        if player_name in row:
            name_index = row.index(player_name)
            start_col = chr(65 + name_index)
            end_col = chr(ord(start_col) + 3)
            start_row = row_index + 1
            end_row = start_row + 13
            return f"{start_col}{start_row}:{end_col}{end_row}"
    return None


def get_values(
    service: Resource, spreadsheet_id: str, sheet_name: str
) -> List[List[str]]:
    # Returns the values of the entire sheet.
    sheet_metadata = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, includeGridData=False)
        .execute()
    )
    sheet = next(
        sheet
        for sheet in sheet_metadata["sheets"]
        if sheet["properties"]["title"] == sheet_name
    )
    max_cols = sheet["properties"]["gridProperties"]["columnCount"]
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=sheet_name)
        .execute()
    )
    values = result.get("values", [])
    for row in values:
        while len(row) < max_cols:
            row.append("")
    return values


def get_range_values(
    service: Resource, spreadsheet_id: str, cell_range: str
) -> List[List[str]]:
    # Returns the values of the specified range in the sheet.
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=cell_range)
        .execute()
    )
    return result.get("values", [])


def next_week_range(week: int) -> str:
    # Returns the range for the specified section for week.
    start_row = (week - 1) * 15 + 2
    end_row = start_row + 13
    return f"B{start_row}:B{end_row}"


def next_week_cell(values: List[List[str]], week: int) -> str:
    # Returns the row and column indices for the top of the next available section for player data for the specified week.
    start_row = (week - 1) * 15 + 1
    max_columns = len(values[0]) if values else 0
    for row in range(start_row, start_row + 15):
        column_index = 3
        while True:
            if row >= len(values):
                column = ""
                temp_index = column_index
                while temp_index >= 0:
                    column = chr(temp_index % 26 + 65) + column
                    temp_index = temp_index // 26 - 1
                return f"{column}{row + 1}"
            if len(values[row]) <= column_index or values[row][column_index] == "":
                column = ""
                temp_index = column_index
                while temp_index >= 0:
                    column = chr(temp_index % 26 + 65) + column
                    temp_index = temp_index // 26 - 1
                return f"{column}{row + 1}"
            column_index += 5
    column = ""
    temp_index = 3
    while temp_index >= 0:
        column = chr(temp_index % 26 + 65) + column
        temp_index = temp_index // 26 - 1
    return f"{column}{start_row + 2}"


def next_data_cell(values: List[List[str]]) -> str:
    # Returns the row and column indices for the top of the next available section for player data.
    letters = ["B", "G", "L", "Q"]
    last_index = 3
    for section in range(1, len(values), 15):
        names_row = values[section]
        details_row = values[section + 1]
        for index, letter in enumerate(letters):
            start_index = index * 5 + 1
            group_cells = [
                (
                    names_row[start_index]
                    if (len(names_row) > start_index and names_row[start_index] != "")
                    else "Empty"
                ),
                (
                    details_row[start_index]
                    if (
                        len(details_row) > start_index
                        and details_row[start_index] == "POKEMON"
                    )
                    else "Empty"
                ),
                (
                    details_row[start_index + 1]
                    if (
                        len(details_row) > start_index + 1
                        and details_row[start_index + 1] == "GAMES"
                    )
                    else "Empty"
                ),
                (
                    details_row[start_index + 2]
                    if (
                        len(details_row) > start_index + 2
                        and details_row[start_index + 2] == "KILLS"
                    )
                    else "Empty"
                ),
                (
                    details_row[start_index + 3]
                    if (
                        len(details_row) > start_index + 3
                        and details_row[start_index + 3] == "DEATHS"
                    )
                    else "Empty"
                ),
            ]
            if any(cell == "Empty" for cell in group_cells):
                return f"{letter}{section + 1}"
            last_index = index
    return f"{letters[(last_index + 1) % len(letters)]}{2 if len(values) == 0 else (len(values) + 2)}"


def check_labels(values: List[List[str]], player_name: str) -> bool:
    # Returns whether the player name is found in values along with the labels of "Pokemon", "Games", "Kills" and "Deaths".
    player_lower = player_name.lower()
    for row_index, row in enumerate(values):
        row_lower = [cell.lower() for cell in row]
        if player_lower in row_lower:
            name_index = row_lower.index(player_lower)
            if row_index + 1 < len(values) and all(
                values[row_index + 1][name_index + i].lower() == label.lower()
                for i, label in enumerate(["POKEMON", "GAMES", "KILLS", "DEATHS"])
            ):
                return True
    return False
