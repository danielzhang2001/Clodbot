"""
The function to set a default Google Sheet as a shortcut for other functions.
"""

from discord.ext.commands import Context
from sheets.sheet import *

default_link = {}


class Set:
    @staticmethod
    def set_default(ctx: Context, sheets_link: str) -> str:
        # Sets the default sheet link.
        if is_valid_sheet(sheet_link, )
        server_id = ctx.guild.id if ctx.guild else 0
        default_link[server_id] = sheets_link
        return f"Default sheet link set to: {sheets_link}"

    @staticmethod
    def get_default(ctx: Context) -> str:
        # Retrieves the default sheet link.
        server_id = ctx.guild.id if ctx.guild else 0
        return default_link.get(server_id)

    @staticmethod
    def has_default(ctx: Context) -> bool:
        # Checks if a default sheet link is set.
        server_id = ctx.guild.id if ctx.guild else 0
        return server_id in default_link
