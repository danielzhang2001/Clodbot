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
            "Clodbot, delete (Google Sheets Link) (Player Name)\n"
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
            "Please follow this format:\n"
            "```Clodbot, giveset random [Number >= 1, Nothing = 1]\n"
            "```"
        )


class InvalidRequest(Exception):
    # Exception raised when an invalid Pokemon set request is found.
    def __init__(self, requests):
        super().__init__("Cannot find sets for " + ", ".join(requests) + ".")


class InvalidParts(Exception):
    # Exception raised when too many parts of a giveset command is used.
    def __init__(self, parts):
        super().__init__(
            "Too many fields provided for {}. Please follow this format:\n"
            "```\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "```".format(", ".join(parts))
        )


class NoAnalyze(Exception):
    # Exception raised when no argument for analyze is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "```"
        )


class NoGiveSet(Exception):
    # Exception raised when no argument for giveset is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "Clodbot, giveset random (Optional Number)\n"
            "```"
        )


class NoUpdate(Exception):
    # Exception raised when no argument for update is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, update (Google Sheets Link) (Replay Link)\n"
            "```"
        )


class NoDelete(Exception):
    # Exception raised when no argument for delete is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, delete (Google Sheets Link) (Player Name)\n"
            "```"
        )


class NoList(Exception):
    # Exception raised when no argument for list is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, list (Google Sheets Link) ['Player' OR 'Pokemon']\n"
            "```"
        )
