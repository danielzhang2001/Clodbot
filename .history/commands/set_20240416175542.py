"""
The function to set a default Google Sheet as a shortcut for other functions.
"""

default_link = {}


def set_default(ctx, sheets_link):
    # Sets the default sheets link.

    server_id = ctx.guild.id if ctx.guild else 0  # Use 0 for DMs or non-guild contexts
    default_sheets_link[server_id] = sheets_link
    return f"Default sheet link set to: {sheets_link}"
