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
            "Clodbot, sheet set (Optional Google Sheets Link) (Optional Sheet Name)\n"
            "Clodbot, sheet default\n"
            "Clodbot, sheet update (Optional Google Sheets Link) (Optional Sheet Name) (Replay Link) [Optional 'New']\n"
            "Clodbot, sheet delete (Optional Google Sheets Link) (Optional Sheet Name) (Player Name)\n"
            "Clodbot, sheet list (Optional Google Sheets Link) (Optional Sheet Name) ['Players' OR 'Pokemon']\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "Clodbot, giveset random (Optional Number)\n"
            "```"
        )


class InvalidReplay(Exception):
    # Exception raised for invalid replay links.
    def __init__(self, link):
        super().__init__(f"**{link}** is an invalid replay link.")


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


class NameDoesNotExist(Exception):
    # Exception raised when the name does not exist in the sheet when calling delete.
    def __init__(self, name):
        super().__init__(f"**{name}** does not exist in the Google Sheets.")


class NoAnalyze(Exception):
    # Exception raised when no argument for analyze is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "```"
        )


class NoSheet(Exception):
    # Exception raised when no argument for sheet is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, sheet set (Google Sheets Link) (Optional Sheet Name)\n"
            "Clodbot, sheet default\n"
            "Clodbot, sheet update (Optional Google Sheets Link) (Optional Sheet Name) (Replay Link) [Optional 'New']\n"
            "Clodbot, sheet delete (Optional Google Sheets Link) (Optional Sheet Name) (Player Name)\n"
            "Clodbot, sheet list (Optional Google Sheets Link) (Optional Sheet Name) ['Players' OR 'Pokemon']\n"
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


class NoSet(Exception):
    # Exception raised when no argument for set is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, sheet set (Google Sheets Link) (Optional Sheet Name)\n"
            "```"
        )


class NoUpdate(Exception):
    # Exception raised when no argument for update is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, sheet update (Optional Google Sheets Link) (Optional Sheet Name) (Replay Link) [Optional 'New']\n"
            "```"
        )


class NoDelete(Exception):
    # Exception raised when no argument for delete is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, sheet delete (Optional Google Sheets Link) (Optional Sheet Name) (Player Name)\n"
            "```"
        )


class NoList(Exception):
    # Exception raised when no argument for list is found.
    def __init__(self):
        super().__init__(
            "Please follow this format:\n"
            "```\n"
            "Clodbot, sheet list (Optional Google Sheets Link) (Optional Sheet Name) ['Player' OR 'Pokemon']\n"
            "```"
        )


class NoPlayers(Exception):
    # Exception raised when there are no player names found in the sheet.
    def __init__(self):
        super().__init__(f"There are no players in the sheet.")


class NoPokemon(Exception):
    # Exception raised when there are no Pokemon names found in the sheet.
    def __init__(self):
        super().__init__(f"There are no Pokemon in the sheet.")


class NoDefault(Exception):
    # Exception raised when there is no existence of a default link.
    def __init__(self):
        super().__init__(
            f"No default sheet link set. You can set it as follows:\n"
            "```\n"
            "Clodbot, sheet set (Google Sheets Link) (Optional Sheet Name)\n"
            "```"
        )


class FullSection(Exception):
    # Exception raised when a player's section is full of Pokemon.
    def __init__(self, player, pokemon):
        super().__init__(f"**{player}**'s section is full: Cannot add **{pokemon}**")


class AuthFailure:
    # Indicates authentication failure.
    pass
