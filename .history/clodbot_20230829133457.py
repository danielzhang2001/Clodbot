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
            # Check if the response status is 200 (OK)
            if response.status == 200:
                print(f"URL for {pokemon_name} is valid!")
            else:
                print(f"URL for {pokemon_name} is not valid. HTTP Status: {response.status}")
                return None
            page = await response.text()

    soup = BeautifulSoup(page, 'html.parser')
    
    # Find the ExportButton which is associated with the set
    export_button = soup.find('button', class_='ExportButton')
    
    # If the button is found, find the associated textarea
    if export_button:
        data_reactid_prefix = export_button['data-reactid'].rsplit('.', maxsplit=1)[0]
        textarea = soup.find('textarea', {'data-reactid': f"{data_reactid_prefix}.0"})
        
        if textarea:
            return textarea.get_text()
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
