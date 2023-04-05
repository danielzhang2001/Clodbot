import discord
from discord.ext import commands
import requests
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.command(name='analyze')
async def analyze_replay(ctx, *args):
    replay_link = ' '.join(args)

    # Scrape battle data from the link
    try:
        raw_data = requests.get(replay_link + '.log').text
    except requests.exceptions.RequestException as e:
        await ctx.send(f"An error occurred while fetching the replay data: {e}")
        return

    # Initialize dictionary to store kill/death numbers
    stats = {}

    # Find all Pokemon in the battle
    pokes = re.findall(r"\|switch\|.*?\|(.*?)(?=\||$)", raw_data)

    print("Found Pokemon:")
    for poke in pokes:
        print(poke)

    # Initialize stats dictionary
    for poke in pokes:
        if poke not in stats:
            stats[poke] = {'kills': 0, 'deaths': 0}

    # Find kills and deaths in the battle
    faints = re.findall(r"\|faint\|.*?: (.*?)$", raw_data, re.MULTILINE)

    print("Fainted Pokemon:")
    for fainted_pokemon in faints:
        print(fainted_pokemon)

    for faint in faints:
        # Find the matching Pokemon in the stats dictionary
        matching_pokemon = None
    for poke in stats:
        if faint in poke:
            matching_pokemon = poke
            break

    # If a matching Pokemon is found, increment the death counter
    if matching_pokemon:
        stats[matching_pokemon]['deaths'] += 1
    else:
        stats[faint] = {'kills': 0, 'deaths': 1}

    moves = re.findall(r"\|move\|.*?\|(.*?):", raw_data)
    for move in moves:
        if move in stats:
            stats[move]['kills'] += 1

    # Format and send the kill/death numbers
    message = ""
    for idx, (poke, stat) in enumerate(stats.items(), start=1):
        message += f"Pokemon {idx}: {poke}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")

bot.run("MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00")
