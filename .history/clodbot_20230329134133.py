import discord
from discord.ext import commands
import requests
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="Clodbot, use ", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.command(name='analyze')
async def analyze_replay(ctx, replay_link: str):
    # Scrape battle data from the link
    raw_data = requests.get(replay_link + '.log').text

    # Initialize dictionary to store kill/death numbers
    stats = {}

    # Find all Pokemon in the battle
    pokes = re.findall(r"\|switch\|.*?\|(.*?):", raw_data)

    # Initialize stats dictionary
    for poke in pokes:
        if poke not in stats:
            stats[poke] = {'kills': 0, 'deaths': 0}

    # Find kills and deaths in the battle
    kills = re.findall(r"\|faint\|(.*?):", raw_data)
    for kill in kills:
        stats[kill]['deaths'] += 1

    moves = re.findall(r"\|move\|.*?\|(.*?):", raw_data)
    for move in moves:
        if move in stats:
            stats[move]['kills'] += 1

    # Format and send the kill/death numbers
    message = ""
    for idx, (poke, stat) in enumerate(stats.items(), start=1):
        message += f"Pokemon {idx}: {poke}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"
    await ctx.send(message)

bot.run("YOUR_BOT_TOKEN")
