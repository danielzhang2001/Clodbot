"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
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

from commands.analyze import Analyze
from commands.giveset import GiveSet

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)

@bot.event
async def on_ready():
    """Print a message when the bot connects to Discord."""
    print(f"{bot.user} has connected to Discord!")


@bot.command(name='analyze')
async def analyze_replay(ctx, *args):
    """Analyzes replay and sends stats in a message to Discord."""
    replay_link = ' '.join(args)
    message = await Analyze.analyze_replay(replay_link)
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")


@bot.command(name='giveset')
async def give_set(ctx, pokemon: str, generation: str = None, format: str = None, *set: str):
    """Sends the first set from Smogon for the given Pokemon name."""
    # Check if only Pokemon is provided
    if generation is None and format is None and not set:
        # Only pokemon was provided, use default generation and format
        set_data = await GiveSet.fetch_set(pokemon)
    else:
        # All arguments were provided, join the set and proceed
        set = ' '.join(set)
        set_data = await GiveSet.fetch_set(pokemon, generation, format, set)
    
    error_keywords = ["not found"]
    if any(keyword in set_data for keyword in error_keywords):
        await ctx.send(set_data)
    else:
        await ctx.send(f"```{set_data}```")

# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)