"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
import discord  # type: ignore
from discord.ext import commands  # type: ignore
from dotenv import load_dotenv  # type: ignore
import aiohttp
from bs4 import BeautifulSoup

from commands.analyze import Analyze

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

async def fetch_smogon_set(pokemon_name: str) -> str:
    """Fetch the first set from Smogon for the given Pokemon name."""
    
    url = f"https://www.smogon.com/dex/ss/pokemon/{pokemon_name.lower()}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            page = await response.text()

    soup = BeautifulSoup(page, 'html.parser')
    set_section = soup.find('div', class_='MoveSetList')
    if not set_section:
        return None

    # Find the first set and return its text content
    first_set = set_section.find('button')
    return first_set.text if first_set else None

@bot.command(name='giveset')
async def give_set(ctx):
    """Temporarily sends a placeholder message 'Creating set...'."""
    await ctx.send("Creating set...")

# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)
