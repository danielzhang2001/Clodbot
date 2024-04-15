"""
All the error messages for Clodbot.
"""


class InvalidReplay(Exception):
    # Exception raised for invalid replay links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid replay link.")


class InvalidSheet(Exception):
    # Exception raised for invalid Google Sheet links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid Google Sheets link.")
