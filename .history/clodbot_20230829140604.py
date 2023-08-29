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
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    # Get the page source after it has been rendered by JavaScript
    page = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page, 'html.parser')
    
    # Find the ExportButton which is associated with the set
    export_button = soup.find('button', class_='ExportButton')
    
    # Print an indicator based on whether the ExportButton is found
    if export_button:
        print(f"Export button found for {pokemon_name}!")
        data_reactid_prefix = export_button['data-reactid'].rsplit('.', maxsplit=1)[0]
        textarea = soup.find('textarea', {'data-reactid': f"{data_reactid_prefix}.0"})
        
        if textarea:
            return textarea.get_text()
    else:
        print(f"No Export button found for {pokemon_name}.")
        
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
