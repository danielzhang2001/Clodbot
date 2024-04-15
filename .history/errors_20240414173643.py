"""
All the error messages for Clodbot.
"""


class InvalidReplay(Exception):
    # Exception raised for invalid replay links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid replay link.")
        self.link = link


class InvalidSheets(Exception):
    # Exception raised for invalid Google Sheets links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid Google Sheets link.")
        self.link = link

    pass


def sheets_error(link):
    return f"**{link}** is an invalid Google Sheets link."
