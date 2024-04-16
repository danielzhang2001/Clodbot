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
    replay_link = " ".join(args)
    if not replay_link:
        await ctx.send(
            "Please provide arguments as shown in the following:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "```"
        )
        return
    message = await Analyze.analyze_replay(replay_link)
    await ctx.send(message)


@bot.command(name="giveset")
async def give_set(ctx: commands.Context, *args: str) -> None:
    # Gives Pokemon set(s) based on Pokemon, Generation (Optional) and Format (Optional) provided, or gives a random set.
    if not args:
        await ctx.send(
            "Please provide arguments as shown in the following:\n"
            "```\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "Clodbot, giveset random (Optional Number)\n"
            "```"
        )
        return
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
            await ctx.send(
                f"Too many arguments provided for {', '.join(invalid_parts)}. Please provide at most a Pokemon, Generation, and Format."
            )
        await GiveSet.set_prompt(ctx, requests)


@bot.command(name="update", aliases=["remove"])
async def update_sheet(ctx: commands.Context, *args: str):
    # Updates sheet with data from replay.
    if len(args) != 2:
        await ctx.send(
            "Please provide arguments as shown in the following:\n"
            "```\n"
            "Clodbot, update (Google Sheets Link) (Replay Link)\n"
            "Clodbot, remove (Google Sheets Link) (Player Name)\n"
            "```"
        )
        return
    command = ctx.invoked_with
    sheets_link, replay_link = args
    creds = Update.authenticate_sheet()
    if command ==
    update_message = await Update.update_sheet(creds, sheets_link, replay_link)
    await ctx.send(update_message)


load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
