"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
import re
import discord  # type: ignore
import aiohttp
from discord.ext import commands  # type: ignore
from dotenv import load_dotenv  # type: ignore
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from commands.analyze import Analyze
from commands.giveset import GiveSet
from commands.update import Update
from commands.delete import Delete
from commands.list import List
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


@bot.command(name="analyze")
async def analyze_replay(ctx: commands.Context, *args: str) -> None:
    # Analyzes replay and sends stats in a message to Discord.
    if not args:
        raise NoAnalyze()
    replay_link = " ".join(args)
    message = await Analyze.analyze_replay(replay_link)
    await ctx.send(message)


@bot.command(name="sheet")
async def sheet(ctx: commands.Context, *args: str):
    # Updates sheet with data from replay.
    command = args[0].lower()
    data = 
    if len(args) != 2:
        if command == "update":
            raise NoUpdate()
        elif command == "delete":
            raise NoDelete()
        elif command == "list":
            raise NoList()
    sheets_link, data = args
    creds = authenticate_sheet()
    if command.lower() == "update":
        message = await Update.update_sheet(creds, sheets_link, data)
    elif command.lower() == "delete":
        message = await Delete.delete_player(creds, sheets_link, data)
    elif command.lower() == "list":
        message = await List.list_data(creds, sheets_link, data)
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
