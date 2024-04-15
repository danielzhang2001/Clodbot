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


class InvalidRandom(InvalidCommandFormat):
    # Exception raised for invalid "giveset random" command format.
    def __init__(self):
        super().__init__(
            "Please follow this format: ```Clodbot, giveset random [Number >= 1, Nothing = 1]```"
        )
