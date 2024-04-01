"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
import re
import discord  # type: ignore
from discord.ext import commands  # type: ignore
from dotenv import load_dotenv  # type: ignore
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from commands.analyze import Analyze
from commands.giveset import GiveSet
from commands.sheets import authenticate_sheets

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
        await ctx.send(
            "Invalid command. Please enter one of the following:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "Clodbot, giveset (Pokemon) (Optional Generation) (Optional Format) [Multiple Using Commas]\n"
            "Clodbot, giveset random (Optional Number)\n"
            "```"
        )


@bot.command(name="analyze")
async def analyze_replay(ctx: commands.Context, replay: str) -> None:
    # Analyzes replay and sends stats in a message to Discord.
    if not replay:
        await ctx.send(
            "Please provide arguments as shown in the following:\n"
            "```\n"
            "Clodbot, analyze (Replay Link)\n"
            "```"
        )
        return
    message = await Analyze.analyze_replay(replay)
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")


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
    if input_str.startswith("random"):
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


@bot.command(name="update")
async def update_sheets(ctx: commands.Context, replay: str, sheets: str):
    creds = authenticate_google_sheets()
    service = build("sheets", "v4", credentials=creds)
    # Your code to interact with the sheets goes here


# COMMAND THAT TAKES IN REPLAY LINK AND GOOGLE SHEETS LINK AND STORES REPLAY INFORMATION IN A SPECIFIC SHEET NAME ON THE GOOGLE SHEETS.
# IF SHEET NAME DOES NOT EXIST, CREATE THE SHEET AND STORE INFORMATION IN
# IF SHEET NAME DOES EXIST, USE THAT SHEET AND UPDATE IT WITH INFORMATION

load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
