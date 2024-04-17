"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""

from typing import List, Tuple
from googleapiclient.discovery import Resource


def next_cell(values: List[List[str]]) -> str:
    # Returns the row and column indices for the top of the next available section.
    letters = ["B", "F", "J", "N"]
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
                        "endColumnIndex": col + 3,
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


def insert_data(
    service: Resource,
    spreadsheet_id: str,
    cell: str,
    player_name: str,
    pokemon: List[Tuple[str, List[int]]],
) -> None:
    # Inserts the Player Name, Pokemon, Kills and Deaths data into the sheet on the specific cell.
    data = (
        [[player_name], ["Pokemon", "Kills", "Deaths"]]
        + [[poke[0]] + poke[1] for poke in pokemon]
        + [[" "] * 3] * max(0, 12 - len(pokemon))
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
    start_col, end_col = cell_range[0], cell_range[cell_range.find(":") + 1]
    start_row, end_row = int(cell_range[1 : cell_range.find(":")]), int(
        cell_range[cell_range.find(":") + 2 :]
    )
    full_range = f"{start_col}{start_row}:{end_col}{end_row}"
    current_values_result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=full_range)
        .execute()
    )
    current_values = current_values_result.get(
        "values", [[] for _ in range(end_row - start_row + 1)]
    )
    print(f"CURRENT VALUES: {current_values}")
    current_pokemon = {row[0]: i for i, row in enumerate(current_values) if row}
    pokemon_updates = []
    for pokemon_name, stats in pokemon_data:
        if pokemon_name in current_pokemon:
            row_index = start_row + current_pokemon[pokemon_name]
            current_kills = int(current_values[current_pokemon[pokemon_name]][1])
            print(f"Current Kills for {pokemon_name}: {current_kills}")
            current_deaths = int(current_values[current_pokemon[pokemon_name]][2])
            print(f"Current Deaths for {pokemon_name}: {current_deaths}")
            updated_kills = current_kills + stats[0]
            print(f"Updated Kills for {pokemon_name}: {updated_kills}")
            updated_deaths = current_deaths + stats[1]
            print(f"Updated Deaths for {pokemon_name}: {updated_deaths}")
            update_range = f"{start_col}{row_index}:{end_col}{row_index}"
            pokemon_updates.append(
                {
                    "range": update_range,
                    "values": [[pokemon_name, updated_kills, updated_deaths]],
                }
            )
        else:
            new_row = end_row + 1
            insert_range = f"{start_col}{new_row}:{end_col}{new_row}"
            pokemon_updates.append(
                {"range": insert_range, "values": [[pokemon_name] + stats]}
            )
            end_row += 1
    if pokemon_updates:
        update_body = {"valueInputOption": "USER_ENTERED", "data": pokemon_updates}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=update_body
        ).execute()


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