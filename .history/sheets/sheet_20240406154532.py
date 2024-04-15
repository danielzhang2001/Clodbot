"""
General functions in updating Google Sheets with Pokemon Showdown replay information.
"""


def next_cell(values: List[List[str]]) -> str:
    # Returns the row and column indices for the top of the next available section.
    letters = ["B", "F", "J", "N"]
    last_index = 0
    for section in range(0, len(values), 15):
        names_row = values[section]
        details_row = values[section + 1]
        for index, letter in enumerate(letters):
            start_index = index * 4
            group_cells = [
                names_row[start_index] if len(names_row) > start_index else "",
                details_row[start_index] if len(details_row) > start_index else "",
                (
                    details_row[start_index + 1]
                    if len(details_row) > start_index + 1
                    else ""
                ),
                (
                    details_row[start_index + 2]
                    if len(details_row) > start_index + 2
                    else ""
                ),
            ]
            if any(cell == "" for cell in group_cells):
                return f"{letter}{section + 2}"
            last_index = index
    return f"{(letters[(last_index + 1) % len(letters)])}{(len(values) + 3)}"
