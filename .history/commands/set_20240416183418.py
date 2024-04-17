"""
The function to set a default Google Sheet as a shortcut for other functions.
"""

from discord.ext.commands import Context

default_link = {}


def set_default(ctx: Context, sheets_link: str) -> str:
    server_id = (
        ctx.guild.id if ctx.guild else 0
    )  # Use guild ID or 0 for direct messages
    default_link[server_id] = sheets_link  # Set the default link
    return f"Default sheet link set to: {sheets_link}"


def get_default(ctx: Context) -> str:
    """Retrieve the default sheet link for the given context, or None if not set."""
    server_id = ctx.guild.id if ctx.guild else 0
    return default_link.get(server_id)


def has_default(ctx: Context) -> bool:
    """Check if a default sheet link is set for the given context."""
    server_id = ctx.guild.id if ctx.guild else 0
    return server_id in default_link
