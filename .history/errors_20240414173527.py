"""
All the error messages for Clodbot.
"""


class InvalidReplayLink(Exception):
    # Exception raised for invalid replay links.

    pass


class InvalidSheetsLink(Exception):
    """Exception raised for invalid Google Sheets links."""

    pass


def replay_error(link):
    return f"**{link}** is an invalid replay link."


def sheets_error(link):
    return f"**{link}** is an invalid Google Sheets link."
