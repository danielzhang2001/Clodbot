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
    range: str,
    player_name: str,
    pokemon: List[Tuple[str, List[int]]],
) -> None:
    # Inserts the Player Name, Pokemon, Kills and Deaths data into the sheet.
    data = (
        [[player_name], ["Pokemon", "Kills", "Deaths"]]
        + [[poke[0]] + poke[1] for poke in pokemon]
        + [[" "] * 3] * max(0, 12 - len(pokemon))
    )
    body = {"values": data}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()


def update_data(
    service: Resource,
    spreadsheet_id: str,
    range: str,
    existing_pokemon: List[str],
    new_pokemon_data: List[Tuple[str, List[int]]],
) -> None:
    # Updates the Pokemon, Kills and Deaths data into the sheet.
    update_requests = []
    insert_requests = []
    base_range, row_range = range.split("!")
    start_row, _ = row_range[1:].split(":")
    start_row_index = int(start_row)
    pokemon_index = {name: idx for idx, name in enumerate(existing_pokemon)}
    current_max_row = start_row_index + len(existing_pokemon) - 1
    for pokemon, new_stats in new_pokemon_data:
        if pokemon in pokemon_index:
            row_to_update = start_row_index + pokemon_index[pokemon]
            current_range = f"{base_range}!C{row_to_update}:E{row_to_update}"
            current_values_result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=current_range)
                .execute()
            )
            current_values = current_values_result.get("values", [[0, 0]])
            if current_values:
                current_kills = (
                    int(current_values[0][0]) if len(current_values[0]) > 0 else 0
                )
                current_deaths = (
                    int(current_values[0][1]) if len(current_values[0]) > 1 else 0
                )
                updated_kills = current_kills + new_stats[0]
                updated_deaths = current_deaths + new_stats[1]
                update_values = [[updated_kills, updated_deaths]]
                update_requests.append(
                    {"range": current_range, "values": update_values}
                )
        else:
            new_row_to_insert = current_max_row + 1
            insert_range = f"{base_range}!A{new_row_to_insert}:E{new_row_to_insert}"
            insert_values = [[pokemon, "Pokemon", new_stats[0], new_stats[1]]]
            insert_requests.append({"range": insert_range, "values": insert_values})
            current_max_row += 1
    if update_requests:
        update_body = {"valueInputOption": "USER_ENTERED", "data": update_requests}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=update_body
        ).execute()
    if insert_requests:
        insert_body = {"valueInputOption": "USER_ENTERED", "data": insert_requests}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=insert_body
        ).execute()


def check_labels(values: List[List[str]], name: str) -> bool:
    # Returns whether the name is found in values alongside with the labels of "Pokemon", "Kills" and "Deaths" associated with it.
    for row_index, row in enumerate(values):
        if (
            name in row
            and row_index + 1 < len(values)
            and values[row_index + 1][name_index] == "Pokemon"
            and values[row_index + 1][name_index + 1] == "Kills"
            and values[row_index + 1][name_index + 2] == "Deaths"
        ):
            return True
    return False
