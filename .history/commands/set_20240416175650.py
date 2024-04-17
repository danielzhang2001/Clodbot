"""
The function to set a default Google Sheet as a shortcut for other functions.
"""

default_link = {}

class Set:
    @staticmethod
    def set_default(ctx, sheets_link):
    # Sets the default sheets link.
    server_id = ctx.guild.id if ctx.guild else 0
    default_link[server_id] = sheets_link
    return f"Default sheet link set to: {sheets_link}"
