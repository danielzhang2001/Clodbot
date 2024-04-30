"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
import discord  # type: ignore
from discord.ext import commands  # type: ignore
from dotenv import load_dotenv  # type: ignore
from commands.analyze import Analyze
from commands.giveset import GiveSet
from commands.managesheet import ManageSheet
from sheets.sheet import authenticate_sheet
from errors import *

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(
    command_prefix=["clodbot, ", "Clodbot, "],
    intents=intents,
    case_insensitive=True,
)


@bot.event
async def on_ready():
    # Print a message when the bot connects to Discord.
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_interaction(interaction: discord.Interaction) -> None:
    # Displays set information and changes button style if necessary when a button is clicked.
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        parts = custom_id.split("_")
        prompt_key = parts[0]
        message_key = parts[1]
        button_key = parts[2]
        pokemon = parts[3]
        generation = parts[4] if parts[4] != "none" else None
        format = parts[5] if parts[5] != "none" else None
        set_name = parts[6]
        request_count = int(parts[7])
        await interaction.response.defer()
        await GiveSet.set_selection(
            interaction,
            prompt_key,
            message_key,
            button_key,
            request_count,
            set_name,
            pokemon,
            generation,
            format,
        )


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    # Handles if a command deviates from the standard format.
    if isinstance(error, commands.CommandNotFound):
        try:
            raise InvalidCommand()
        except InvalidCommand as e:
            await ctx.send(str(e))
    else:
        await ctx.send(f'{str(error).split(": ", 2)[-1]}')


@bot.command(name="help")
async def help_command(ctx: commands.Context) -> None:
    message = (
        "**COMMANDS:\n\n"
        "**Clodbot, analyze (Pokemon Showdown Replay Link)** to display the stats from the replay on Discord.\n"
        "**Clodbot, sheet set (Google Sheets Link)** to set the default Google Sheets link for future 'sheet' commands.\n"
        "**Clodbot, sheet default** to display the default sheet link on Discord.\n"
        "**Clodbot, sheet update (Optional Google Sheets Link) (Pokemon Showdown Replay Link)** to update the stats from the replay onto a 'Stats' sheet in the link. Uses default link if Google Sheets link not provided.\n"
        "**Clodbot, sheet delete (Optional Google Sheets Link) (Player Name)** to delete the stats section with Player Name from the 'Stats' sheet in the link. Uses default link if Google Sheets link not provided.\n"
        "**Clodbot, sheet list (Optional Google Sheets Link) ['Players' OR 'Pokemon']** to display either all Player stats (if 'Players') or all Pokemon stats (if 'Pokemon') from the 'Stats' sheet in the link on Discord. Uses default link if Google Sheets link not provided.\n"
        "**Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]** to display prompt(s) for set selection based on the provided parameters. Uses first format found if format not provided and latest generation if generation not provided.\n"
        "**Clodbot, giveset random (Optional Number)** to display random set(s) for the specified amount of random Pokemon. Assumes one if no number given.\n\n"
        "For more information, please visit the official website for Clodbot here"
    )
    await ctx.send(message)


@bot.command(name="analyze")
async def analyze_replay(ctx: commands.Context, *args: str) -> None:
    # Analyzes replay and sends stats in a message to Discord.
    if not args:
        raise NoAnalyze()
    replay_link = " ".join(args)
    message = await Analyze.analyze_replay(replay_link)
    await ctx.send(message)


@bot.command(name="sheet")
async def manage_sheet(ctx: commands.Context, *args: str) -> None:
    # Manages Google Sheets data.
    if not args:
        raise NoSheet()
    command = args[0].lower()
    remaining = args[1:]
    server_id = ctx.guild.id
    creds = await authenticate_sheet(server_id)
    if command not in ["set", "default", "update", "delete", "list"]:
        raise NoSheet()
    if command == "default":
        message = ManageSheet.display_default(ctx, creds)
    elif command == "set":
        if len(remaining) != 1:
            raise NoSet()
        message = await ManageSheet.set_default(ctx, server_id, creds, remaining[0])
    else:
        if len(remaining) == 1:
            if ManageSheet.has_default(ctx):
                sheet_link = ManageSheet.get_default(ctx)
                data = remaining[0]
            else:
                raise NoDefault()
        elif len(remaining) == 2:
            sheet_link, data = remaining
        else:
            if command == "update":
                raise NoUpdate()
            elif command == "delete":
                raise NoDelete()
            elif command == "list":
                raise NoList()
            return
        if command == "update":
            message = await ManageSheet.update_sheet(server_id, creds, sheet_link, data)
        elif command == "delete":
            message = await ManageSheet.delete_player(
                server_id, creds, sheet_link, data
            )
        elif command == "list":
            message = await ManageSheet.list_data(server_id, creds, sheet_link, data)
    await ctx.send(message)


@bot.command(name="giveset")
async def give_set(ctx: commands.Context, *args: str) -> None:
    # Gives Pokemon set(s) based on Pokemon, Generation (Optional) and Format (Optional) provided, or gives a random set.
    if not args:
        raise NoGiveSet()
    input_str = " ".join(args).strip()
    requests = []
    invalid_parts = []
    if input_str.lower().startswith("random"):
        await GiveSet.fetch_random_sets(ctx, input_str)
    else:
        parts = [part.strip() for part in input_str.split(",")]
        for part in parts:
            request_parts = part.strip().split()
            if len(request_parts) > 3:
                invalid_parts.append(f"**{part}**")
                continue
            requests.append(
                {
                    "pokemon": request_parts[0],
                    "generation": request_parts[1] if len(request_parts) > 1 else None,
                    "format": request_parts[2] if len(request_parts) == 3 else None,
                }
            )
        if invalid_parts:
            await ctx.send(InvalidParts(invalid_parts).args[0])
        await GiveSet.set_prompt(ctx, requests)


load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
