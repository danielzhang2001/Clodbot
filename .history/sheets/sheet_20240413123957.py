"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""

from typing import Optional, List, Dict, Tuple
from googleapiclient.discovery import Resource


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
    data = (
        [[player_name], ["POKEMON", "GAMES", "KILLS", "DEATHS"]]
        + [[poke[0], 1] + poke[1] for poke in pokemon]
        + [[" "] * 4] * max(0, 12 - len(pokemon))
    )
    data_range = f"{col}{row}:{chr(ord(col) + 3)}{row + num_rows + 1}"
    section_range = f"{sheet_name}!{data_range}"
    body = {"values": data}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=cell,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    name_range = f"{sheet_name}!{col}{row}:{chr(ord(col) + 3)}{row}"
    merge_cells(service, spreadsheet_id, sheet_id, name_range)
    outline_cells(service, spreadsheet_id, sheet_id, section_range)
    color_cells(service, spreadsheet_id, sheet_id, section_range)
    format_text(service, spreadsheet_id, sheet_id, section_range)


def update_data(
    service: Resource,
    spreadsheet_id: str,
    sheet_id: int,
    cell_range: str,
    pokemon_data: List[Tuple[str, List[int]]],
) -> None:
    # Updates the Pokemon, Kills and Deaths data into the sheet.
    sheet_name, cell_range = cell_range.split("!")
    start_range, end_range = cell_range.split(":")
    start_col = "".join(filter(str.isalpha, start_range))
    end_col = "".join(filter(str.isalpha, end_range))
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
    insert_range = f"{sheet_name}!{start_col}{insert_row}:{end_col}{insert_row}"
    updates.append(
        {
            "range": insert_range,
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


def merge_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Merges the cells containing the name for formatting purposes.
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
    # Bolds and colors the outline gray of all the cells in the range for formatting purposes.
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
    # Colors all the cells in the range for formatting purposes.
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
                            "firstBandColor": {
                                "red": 0,
                                "green": 0,
                                "blue": 0,
                            },
                            "secondBandColor": {
                                "red": 0,
                                "green": 0.15,
                                "blue": 0.5,
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


def color_text(
    service: Resource, spreadsheet_id: str, sheet_id: int, cell_range: str
) -> None:
    # Colors all the text in the range white for formatting purposes.
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
                        "startRowIndex": start_row - 1,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_index,
                        "endColumnIndex": end_index + 1,
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


def check_labels(values: List[List[str]], name: str) -> bool:
    # Returns whether the name is found in values alongside with the labels of "Pokemon", "Games", "Kills" and "Deaths" associated with it.
    for row_index, row in enumerate(values):
        try:
            name_index = row.index(name)
            if row_index + 1 < len(values) and all(
                values[row_index + 1][name_index + i] == label
                for i, label in enumerate(["Pokemon", "Games", "Kills", "Deaths"])
            ):
                return True
        except ValueError:
            continue
    return False


def get_range(values: List[List[str]], name: str) -> str:
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
