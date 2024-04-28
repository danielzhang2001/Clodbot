"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""

import pickle
import os.path
import asyncio
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from typing import Optional, List, Dict, Tuple

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


async def authenticate_sheet(server_id: int, force_login: bool = False) -> Credentials:
    # Authenticates sheet functionality with appropriate credentials.
    creds_directory = "sheets"
    if not os.path.exists(creds_directory):
        os.makedirs(creds_directory)
    token_filename = f"token_{server_id}.pickle"
    token_path = os.path.join(creds_directory, token_filename)
    credentials_path = os.path.join(creds_directory, "credentials.json")
    creds = None
    if os.path.exists(token_path) and not force_login:
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = await asyncio.to_thread(flow.run_local_server, port=0)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)
    return creds


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
    cell_range = f"{sheet_name}!{col}{row}:{chr(ord(col) + 3)}{row + num_rows + 1}"
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
    format_cells(service, spreadsheet_id, sheet_id, cell_range)
    format_text(service, spreadsheet_id, sheet_id, cell_range)


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
    sheet_id: int,
    cell_range: str,
    pokemon_data: List[Tuple[str, List[int]]],
) -> None:
    # Updates the Pokemon, Kills and Deaths data into the sheet.
    sheet_name, cell_range = cell_range.split("!")
    print(f"cell range: {cell_range}")
    start_range, end_range = cell_range.split(":")
    print(f"start range: {start_range}")
    print(f"end range: {end_range}")
    start_col = "".join(filter(str.isalpha, start_range))
    end_col = "".join(filter(str.isalpha, end_range))
    print(f"start col: {start_col}")
    print(f"end col: {end_col}")
    start_row = int("".join(filter(str.isdigit, start_range)))
    end_row = int("".join(filter(str.isdigit, end_range)))
    full_range = f"{sheet_name}!{start_col}{start_row}:{end_col}{end_row}"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=full_range)
        .execute()
    )
    current_values = result.get("values", [[] for _ in range(end_row - start_row + 1)])
    current_pokemon = {}
    empty_row = None
    for idx, row in enumerate(current_values, start=start_row):
        if row:
            current_pokemon[row[0]] = idx
        elif empty_row is None:
            empty_row = idx
    updates = []
    for pokemon_name, new_stats in pokemon_data:
        if pokemon_name in current_pokemon:
            update_pokemon(
                sheet_name,
                start_col,
                end_col,
                start_row,
                current_pokemon,
                current_values,
                pokemon_name,
                new_stats,
                updates,
            )
        else:
            empty_row, end_row = add_pokemon(
                sheet_name,
                start_col,
                end_col,
                pokemon_name,
                new_stats,
                empty_row,
                end_row,
                updates,
            )
    if updates:
        widen_columns(service, spreadsheet_id, sheet_id)
        update_body = {"valueInputOption": "USER_ENTERED", "data": updates}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=update_body
        ).execute()


def add_pokemon(
    sheet_name: str,
    start_col: str,
    end_col: str,
    pokemon_name: str,
    new_stats: List[int],
    empty_row: Optional[int],
    end_row: int,
    updates: List[Dict[str, List[Tuple[str, int, int]]]],
) -> Tuple[Optional[int], int]:
    # Adds new Pokemon entries to the appropriate section in the sheet.
    insert_row = empty_row if empty_row is not None else end_row + 1
    cell_range = f"{sheet_name}!{start_col}{insert_row}:{end_col}{insert_row}"
    print(f"add pokemon cell range: {cell_range}")
    updates.append(
        {
            "range": cell_range,
            "values": [[pokemon_name, 1, new_stats[0], new_stats[1]]],
        }
    )
    if empty_row is not None:
        empty_row += 1
    else:
        end_row += 1
    return empty_row, end_row


def update_pokemon(
    sheet_name: str,
    start_col: str,
    end_col: str,
    start_row: int,
    current_pokemon: Dict[str, int],
    current_values: List[List[str]],
    pokemon_name: str,
    new_stats: List[int],
    updates: List[Dict[str, List[Tuple[str, int, int]]]],
) -> None:
    # Updates existing Pokemon entries to the appropriate section in the sheet.
    row_index = current_pokemon[pokemon_name]
    current_games = int(current_values[row_index - start_row][1])
    current_kills = int(current_values[row_index - start_row][2])
    current_deaths = int(current_values[row_index - start_row][3])
    updated_games = current_games + 1
    updated_kills = current_kills + new_stats[0]
    updated_deaths = current_deaths + new_stats[1]
    update_range = f"{sheet_name}!{start_col}{row_index}:{end_col}{row_index}"
    updates.append(
        {
            "range": update_range,
            "values": [[pokemon_name, updated_games, updated_kills, updated_deaths]],
        }
    )


def create_player_message(values: List[List[str]]) -> str:
    # Creates the message when asked to list players in the sheet.
    sorted_players = sorted(
        get_sheet_players(values), key=lambda x: (-int(x[1]), int(x[2]))
    )
    message = "**PLAYERS:**\n```"
    message += "\n".join(
        [
            f"{name} (Kills: {kills}, Deaths: {deaths})"
            for name, kills, deaths in sorted_players
        ]
    )
    message += "\n```"
    return message


def create_pokemon_message(values: List[List[str]]) -> str:
    # Creates the message when asked to list Pokemon in the sheet.
    pokemon = sorted(get_sheet_pokemon(values), key=lambda x: (-int(x[1]), int(x[2])))
    message = "**POKEMON:**\n```"
    message += "\n".join(
        [
            f"{player}'s {name} (Kills: {kills}, Deaths: {deaths})"
            for player, name, kills, deaths in pokemon
        ]
    )
    message += "\n```"
    return message


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


def format_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Formats all of the cells for the player section.
    name_range = f"{cell_range.split('!')[0]}!{cell_range.split('!')[1].split(':')[0]}:{cell_range.split(':')[1][0]}{cell_range.split('!')[1].split(':')[0][1:]}"
    merge_cells(service, spreadsheet_id, sheet_id, name_range)
    outline_cells(service, spreadsheet_id, sheet_id, cell_range)
    color_cells(service, spreadsheet_id, sheet_id, cell_range)


def format_text(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Formats all of the text for the player section.
    header_range = f"{cell_range.split('!')[0]}!{cell_range.split('!')[1].split(':')[0]}:{cell_range.split(':')[1][0]}{int(cell_range.split('!')[1].split(':')[0][1:]) + 1}"
    style_text(service, spreadsheet_id, sheet_id, cell_range)
    center_text(service, spreadsheet_id, sheet_id, header_range)


def merge_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Merges the cells in the range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    body = {
        "requests": [
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
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
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    body = {
        "requests": [
            {
                "updateBorders": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
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


def color_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the cells in the range.
    _, cell_range = cell_range.split("!")
    start_cell, end_cell = cell_range.split(":")
    start_row = int("".join(filter(str.isdigit, start_cell))) - 1
    end_row = int("".join(filter(str.isdigit, end_cell)))
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    body = {
        "requests": [
            {
                "addBanding": {
                    "bandedRange": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": start_row,
                            "endRowIndex": end_row,
                            "startColumnIndex": start_col,
                            "endColumnIndex": end_col,
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
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
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
    for banding_id in banding_ids:
        requests.append({"deleteBanding": {"bandedRangeId": banding_id}})
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
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
    body = {
        "requests": [
            {
                "updateCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "fields": "userEnteredValue",
                    "rows": [
                        {
                            "values": [
                                {"userEnteredValue": {}}
                                for _ in range(start_col, end_col)
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


def style_text(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the text in the range and sets the font and font size.
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
    start_col = ord(start_cell[0]) - ord("A")
    end_col = ord(end_cell[0]) - ord("A") + 1
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
                or brange.get("endColumnIndex", 0) <= start_col
                or brange.get("startColumnIndex", float("inf")) >= end_col
            )
        ):
            overlapping_ids.append(banded_range["bandedRangeId"])
    return overlapping_ids


def get_sheet_players(values: List[List[str]]) -> List[List[str]]:
    # Returns a list of all the player names and their total kills/deaths.
    players = []
    if not values or len(values) < 3:
        return players
    for i in range(0, len(values), 15):
        header_row = values[i]
        for index, name in enumerate(header_row):
            if name.strip() == "":
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
    print(f"values: {values}")
    pokemon = []
    for i in range(2, len(values), 15):
        for j in range(i, min(i + 12, len(values))):
            row = values[j]
            for idx, name in enumerate(row):
                if name.strip() and not (
                    name.strip().replace(".", "", 1).isdigit()
                    and name.strip().count(".") <= 1
                ):
                    if idx + 2 < len(row) and idx + 3 < len(row):
                        kills = row[idx + 2].strip()
                        deaths = row[idx + 3].strip()
                        pokemon.append([name.strip(), kills, deaths])
    return pokemon


def get_stat_range(values: List[List[str]], name: str) -> str:
    # Searches for the name and returns the range of the section with Pokemon stats associated with that name.
    for row_index, row in enumerate(values):
        if name in row:
            name_index = row.index(name) + 1
            start_col = chr(65 + name_index)
            end_col = chr(ord(start_col) + 3)
            start_row = row_index + 4
            end_row = start_row + 11
            return f"{start_col}{start_row}:{end_col}{end_row}"
    return None


def get_section_range(values: List[List[str]], player_name: str) -> str:
    # Searches for the name and returns the range of the entire section for that name.
    for row_index, row in enumerate(values):
        if player_name in row:
            name_index = row.index(player_name) + 1
            start_col = chr(65 + name_index)
            end_col = chr(ord(start_col) + 3)
            start_row = row_index + 2
            end_row = start_row + 13
            return f"{start_col}{start_row}:{end_col}{end_row}"
    return None


def next_cell(values: List[List[str]]) -> str:
    # Returns the row and column indices for the top of the next available section.
    letters = ["B", "G", "L", "Q"]
    last_index = 3
    for section in range(0, len(values), 15):
        names_row = values[section]
        details_row = values[section + 1]
        for index, letter in enumerate(letters):
            start_index = index * 5
            group_cells = [
                (
                    names_row[start_index]
                    if (len(names_row) > start_index and names_row[start_index] != "")
                    else "Invalid"
                ),
                (
                    details_row[start_index]
                    if (
                        len(details_row) > start_index
                        and details_row[start_index] == "POKEMON"
                    )
                    else "Invalid"
                ),
                (
                    details_row[start_index + 1]
                    if (
                        len(details_row) > start_index + 1
                        and details_row[start_index + 1] == "GAMES"
                    )
                    else "Invalid"
                ),
                (
                    details_row[start_index + 2]
                    if (
                        len(details_row) > start_index + 2
                        and details_row[start_index + 2] == "KILLS"
                    )
                    else "Invalid"
                ),
                (
                    details_row[start_index + 3]
                    if (
                        len(details_row) > start_index + 3
                        and details_row[start_index + 3] == "DEATHS"
                    )
                    else "Invalid"
                ),
            ]
            if any(cell == "Invalid" for cell in group_cells):
                return f"{letter}{section + 2}"
            last_index = index
    return f"{letters[(last_index + 1) % len(letters)]}{2 if len(values) == 0 else (len(values) + 3)}"


def check_labels(values: List[List[str]], player_name: str) -> bool:
    # Returns whether the player name is found in values along with the labels of "Pokemon", "Games", "Kills" and "Deaths".
    for row_index, row in enumerate(values):
        if player_name in row:
            name_index = row.index(player_name)
            if row_index + 1 < len(values) and all(
                values[row_index + 1][name_index + i] == label
                for i, label in enumerate(["POKEMON", "GAMES", "KILLS", "DEATHS"])
            ):
                return True
    return False


def is_valid_sheet(
    creds: Credentials,
    sheet_link: str,
) -> bool:
    # Checks if the sheet link is valid.
    try:
        spreadsheet_id = sheet_link.split("/d/")[1].split("/")[0]
        service = build("sheets", "v4", credentials=creds)
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        return True
    except (IndexError, HttpError):
        return False
