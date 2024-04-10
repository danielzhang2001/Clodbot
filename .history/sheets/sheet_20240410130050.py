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
    # Correctly parse the row start from range, assuming range format like "Stats!B2:P285"
    base_range, row_range = range.split("!")
    start_row, end_row = (
        row_range[1:].split(":")[0],
        row_range.split(":")[1],
    )  # This assumes the format is always B2:P285 or similar
    start_row_index = int(start_row)  # Correct conversion to integer

    pokemon_index = {name: idx for idx, name in enumerate(existing_pokemon)}
    for pokemon, stats in new_pokemon_data:
        if pokemon in pokemon_index:
            row_to_update = (
                start_row_index + pokemon_index[pokemon]
            )  # Corrected logic to add index to base row
            update_range = f"{base_range}!C{row_to_update}:E{row_to_update}"
            current_kills, current_deaths = stats
            body = {"values": [[current_kills, current_deaths]]}
            update_requests.append({"range": update_range, "values": body["values"]})

    if update_requests:
        body = {"valueInputOption": "USER_ENTERED", "data": update_requests}
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id, body=body
        ).execute()
