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
    # Print a message when the bot connects to Discord.
    print(f"{bot.user} has connected to Discord!")


@bot.command(name="analyze")
async def analyze_replay(ctx, *args):
    # Analyzes replay and sends stats in a message to Discord.
    replay_link = " ".join(args)
    message = await Analyze.analyze_replay(replay_link)
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")


@bot.command(name="giveset")
async def give_set(
    ctx, pokemon: str, generation: str = None, format: str = None, *set: str
):
    # Sends the Pokemon set from Smogon according to Pokemon, Generation, Format and Set. If only Pokemon provided, allows selection from a choice of sets given most recent generation and first format found.
    set_data = ""
    if generation is None and format is None and not set:
        sets = await GiveSet.fetch_set(pokemon)
        if sets:
            await GiveSet.set_prompt(ctx, pokemon, sets)
        else:
            await ctx.send(f"No sets found for {pokemon}.")
    else:
        set = " ".join(set)
        set_data = await GiveSet.fetch_set(pokemon, generation, format, set)
    await ctx.send(set_data)


@bot.listen("on_message")
async def on_message(message):
    # Listener for on_message to handle set selection response
    if message.author == bot.user:
        return
    ctx = await bot.get_context(message)
    if ctx.valid:
        return
    if message.channel.id in GiveSet.awaiting_response:
        await GiveSet.set_selection(ctx, message)


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
