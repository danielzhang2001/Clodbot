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
async def give_set(ctx, pokemon_name: str, generation: str, format: str, *set_name: str):
    """Sends the first set from Smogon for the given Pokemon name."""
    set_name = ' '.join(set_name)
    set_data = await GiveSet.fetch_set(pokemon_name, generation, format, set_name)
    # Check for error messages before sending set data
    error_messages = [
        f"Generation \"{generation}\" Not Found.",
        f"Pokemon \"{pokemon_name}\" not found or doesn't exist in Generation \"{generation}\"."
        f"Format \"{format}\" Not Found.",
        f"Set Type \"{set_name}\" Not Found."
    ]
    if set_data in error_messages:
        await ctx.send(set_data)
    else:
        await ctx.send(f"```{set_data}```")

# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)