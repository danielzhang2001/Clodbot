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
    help_command=None,
)


@bot.event
async def on_ready():
    # Print a message when the bot connects to Discord.
    print(f"{bot.user} has connected to Discord!")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening, name="clodbot, help"
        )
    )


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
async def help(ctx: commands.Context) -> None:
    # Displays all commands with a link to the website for help.
    message = (
        "**COMMANDS:**\n\n"
        "> **Clodbot, analyze (Pokemon Showdown Replay Link)** to display the stats from the replay on Discord.\n"
        "> \n"
        "> **Clodbot, sheet set (Google Sheets Link) (Optional Sheet Name)** to set the default Google Sheets link and sheet name for future sheet commands. If not provided, sheet name defaults to 'Stats'.\n"
        "> \n"
        "> **Clodbot, sheet default** to display the default sheet link and sheet name on Discord.\n"
        "> \n"
        "> **Clodbot, sheet update (Optional Google Sheets Link) (Optional Sheet Name) (Pokemon Showdown Replay Link) [Optional Week#] (Optional Showdown Name->New Name [Multiple])** to update the stats from the replay onto the sheet name in the link. If not provided, sheet name defaults to 'Stats'. If a week number is specified, the replay will go into a week section. You can also assign a new name to a player name in the replay, and this parameter can be applied multiple times.\n"
        "> \n"
        "> **Clodbot, sheet delete (Optional Google Sheets Link) (Optional Sheet Name) (Player Name)** to delete the stats section with Player Name from the sheet name in the link. If not provided, sheet name defaults to 'Stats'.\n"
        "> \n"
        "> **Clodbot, sheet list (Optional Google Sheets Link) (Optional Sheet Name) ['Players' OR 'Pokemon']** to display either all Player stats or all Pokemon stats from the sheet name in the link on Discord. If not provided, sheet name defaults to 'Stats'.\n"
        "> \n"
        "> **Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]** to display prompt(s) for set selection based on the provided parameters.\n"
        "> \n"
        "> **Clodbot, giveset random (Optional Number)** to display random set(s) for the specified amount of random Pokemon.\n\n"
        "For more information, please visit the official website for Clodbot [**HERE**](https://clodbot.com)."
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
    server_id = ctx.guild.id
    if command not in ["set", "default", "update", "delete", "list"]:
        raise NoSheet()
    remaining = []
    name_dict = {}
    found_arrow = True
    week = None
    for arg in reversed(args[1:]):
        if "->" in arg and found_arrow:
            parts = arg.split("->")
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                name_dict[key] = value
        else:
            found_arrow = False
            remaining.insert(0, arg)
    if command == "default":
        if await ManageSheet.has_default(server_id):
            message = await ManageSheet.get_default(server_id)
        else:
            raise NoDefault()
    elif command == "set":
        if len(remaining) not in (1, 2):
            raise NoSet()
        sheet_link = remaining[0]
        sheet_name = None
        if len(remaining) == 2:
            sheet_name = remaining[1]
        creds = await authenticate_sheet(ctx, server_id, sheet_link)
        if isinstance(creds, AuthFailure):
            return
        message = await ManageSheet.set_default(
            server_id, creds, remaining[0], sheet_name
        )
    else:
        remaining_lower = [item.lower() for item in remaining]
        if len(remaining) == 1 or (
            command == "update"
            and len(remaining) == 2
            and remaining_lower[1].startswith("week")
        ):
            if len(remaining_lower) > 1 and remaining_lower[1].startswith("week"):
                week = int(remaining_lower[1][4:])
            if await ManageSheet.has_default(server_id):
                sheet_link, sheet_name = await ManageSheet.use_default(server_id)
                data = remaining[0]
            else:
                raise NoDefault()
        elif len(remaining) == 2 or (
            command == "update"
            and len(remaining) == 3
            and remaining_lower[2].startswith("week")
        ):
            if len(remaining_lower) > 2 and remaining_lower[2].startswith("week"):
                week = int(remaining_lower[2][4:])
            sheet_link = remaining[0]
            data = remaining[1]
            sheet_name = "Stats"
        elif len(remaining) == 3 or (
            command == "update"
            and len(remaining) == 4
            and remaining_lower[3].startswith("week")
        ):
            if len(remaining_lower) > 3 and remaining_lower[3].startswith("week"):
                week = int(remaining_lower[3][4:])
            sheet_link = remaining[0]
            sheet_name = remaining[1]
            data = remaining[2]
        else:
            if command == "update":
                raise NoUpdate()
            elif command == "delete":
                raise NoDelete()
            elif command == "list":
                raise NoList()
            return
        creds = await authenticate_sheet(ctx, server_id, sheet_link)
        if isinstance(creds, AuthFailure):
            return
        if command == "update":
            message = await ManageSheet.update_sheet(
                ctx, server_id, creds, sheet_link, sheet_name, data, name_dict, week
            )
        elif command == "delete":
            message = await ManageSheet.delete_player(
                ctx, server_id, creds, sheet_link, sheet_name, data
            )
        elif command == "list":
            message = await ManageSheet.list_data(
                ctx, server_id, creds, sheet_link, sheet_name, data
            )
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
