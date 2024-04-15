"""
All the error messages for Clodbot.
"""


class InvalidReplay(Exception):
    # Exception raised for invalid replay links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid replay link.")


class InvalidSheets(Exception):
    # Exception raised for invalid Google Sheets links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid Google Sheets link.")
