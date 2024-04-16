"""
All the error messages for Clodbot.
"""


class InvalidCommand(Exception):
    # Exception raised when an invalid command is used.
    def __init__(self):
        super().__init__(
            "Invalid command. Please enter one of the following:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "Clodbot, update (Google Sheets Link) (Replay Link)\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "Clodbot, giveset random (Optional Number)\n"
            "```"
        )


class InvalidReplay(Exception):
    # Exception raised for invalid replay links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid replay link.")


class InvalidSheet(Exception):
    # Exception raised for invalid Google Sheet links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid Google Sheets link.")


class InvalidRandom(Exception):
    # Exception raised for invalid number provided for the random command.
    def __init__(self):
        super().__init__(
            "Please follow this format: ```Clodbot, giveset random [Number >= 1, Nothing = 1]```"
        )


class InvalidRequest(Exception):
    # Exception raised when an invalid Pokemon set request is found.
    def __init__(self, requests):
        super().__init__("Cannot find sets for " + ", ".join(requests) + ".")
