"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""

from typing import Optional, List, Dict, Tuple
from googleapiclient.discovery import Resource


def next_cell(values: List[List[str]]) -> str:
    # Returns the row and column indices for the top of the next available section.
    letters = ["B", "G", "L", "Q"]
    last_index = 3
    for section in range(0, len(values), 15):
        names_row = values[section]
        details_row = values[section + 1]
        for index, letter in enumerate(letters):
            start_index = index * 4
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
                        and details_row[start_index] == "Pokemon"
                    )
                    else "Invalid"
                ),
                (
                    details_row[start_index + 1]
                    if (
                        len(details_row) > start_index + 1
                        and details_row[start_index + 1] == "Kills"
                    )
                    else "Invalid"
                ),
                (
                    details_row[start_index + 2]
                    if (
                        len(details_row) > start_index + 2
                        and details_row[start_index + 2] == "Deaths"
                    )
                    else "Invalid"
                ),
            ]
            if any(cell == "Invalid" for cell in group_cells):
                return f"{letter}{section + 2}"
            last_index = index
    return f"{letters[(last_index + 1) % len(letters)]}{2 if len(values) == 0 else (len(values) + 3)}"


def merge_cells(
    service: Resource, spreadsheet_id: str, sheet_id: int, col: str, row: int
) -> None:
    # Merges the cells containing the name for formatting purposes.
    col = ord(col) - ord("A")
    merge_body = {
        "requests": [
            {
                "mergeCells": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row - 1,
                        "endRowIndex": row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 4,
                    },
                    "mergeType": "MERGE_ALL",
                }
            },
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": row - 1,
                        "endRowIndex": row,
                        "startColumnIndex": col,
                        "endColumnIndex": col + 1,
                    },
                    "cell": {"userEnteredFormat": {"horizontalAlignment": "CENTER"}},
                    "fields": "userEnteredFormat.horizontalAlignment",
                }
            },
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=merge_body,
    ).execute()


def add_data(
    service: Resource,
    spreadsheet_id: str,
    cell: str,
    player_name: str,
    pokemon: List[Tuple[str, List[int]]],
) -> None:
    # Adds the Player Name, Pokemon, Games Played, Kills and Deaths data into the sheet on the specific cell.
    data = (
        [[player_name], ["Pokemon", "Games Played", "Kills", "Deaths"]]
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


def update_data(
    service: Resource,
    spreadsheet_id: str,
    cell_range: str,
    pokemon_data: List[Tuple[str, List[int]]],
) -> None:
    # Updates the Pokemon, Kills and Deaths data into the sheet.
    sheet_name, range_part = cell_range.split("!")
    start_range, end_range = range_part.split(":")
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
    updated_kills = current_kills + new_stats[0]
    updated_deaths = current_deaths + new_stats[1]
    update_range = f"{sheet_name}!{start_col}{row_index}:{end_col}{row_index}"
    updates.append(
        {
            "range": update_range,
            "values": [[pokemon_name, updated_kills, updated_deaths]],
        }
    )


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
        {"range": insert_range, "values": [[pokemon_name, new_stats[0], new_stats[1]]]}
    )
    if empty_row is not None:
        empty_row += 1
    else:
        end_row += 1
    return empty_row, end_row


def check_labels(values: List[List[str]], name: str) -> bool:
    # Returns whether the name is found in values alongside with the labels of "Pokemon", "Kills" and "Deaths" associated with it.
    for row_index, row in enumerate(values):
        try:
            name_index = row.index(name)
            if row_index + 1 < len(values) and all(
                values[row_index + 1][name_index + i] == label
                for i, label in enumerate(["Pokemon", "Kills", "Deaths"])
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
            end_col = chr(ord(start_col) + 2)
            start_row = row_index + 4
            end_row = start_row + 11
            return f"{start_col}{start_row}:{end_col}{end_row}"
    return None
