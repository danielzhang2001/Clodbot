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
    """Fetch the first set from Smogon for the given Pokemon name using Selenium."""
    
    url = f"https://www.smogon.com/dex/sv/pokemon/{pokemon_name.lower()}"
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--log-level=3")  # Suppress logging
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Try to find the ExportButton and click it
    try:
        export_button = driver.find_element_by_xpath("//button[contains(@class, 'ExportButton')]")
        export_button.click()
        print(f"Export button found and clicked for {pokemon_name}!")
    except Exception as e:
        print(f"No Export button found for {pokemon_name}.")
        driver.quit()
        return None

    # After clicking, try to retrieve the textarea content
    try:
        # You might want to add a short delay here if necessary
        # from time import sleep
        # sleep(2)
        textarea = driver.find_element_by_tag_name("textarea")
        set_data = textarea.text
        print(f"Textarea found for {pokemon_name}!")
        driver.quit()
        return set_data
    except Exception as e:
        print(f"No Textarea found for {pokemon_name}.")
        driver.quit()
        return None

@bot.command(name='giveset')
async def give_set(ctx, pokemon_name: str):
    """Sends the first set from Smogon for the given Pokemon name."""
    
    set_data = await fetch_smogon_set(pokemon_name)
    if set_data:
        await ctx.send(f"```{set_data}```")  # The triple backticks format the message as code in Discord
    else:
        await ctx.send(f"No set found for {pokemon_name} on Smogon.")

# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)
