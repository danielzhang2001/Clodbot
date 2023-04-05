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
    pokes = re.findall(r"\|poke\|\w+\|(.*?)(?=\||$)", raw_data)

    print("Found Pokemon:")
    for poke in pokes:
        print(poke)

    # Initialize stats dictionary
    for poke in pokes:
        if poke not in stats:
            stats[poke] = {'kills': 0, 'deaths': 0}

    # Find kills and deaths in the battle
    faints = re.findall(r"\|faint\|.*?: (.*?)$", raw_data, re.MULTILINE)

    # Create a dictionary to store the mapping between nicknames and actual Pokemon names
    nickname_to_pokemon = {}
    switch_lines = re.findall(r"\|switch\|.*?:(.*?)\|(.*?)(?=\||$)", raw_data)

    for nickname, pokemon in switch_lines:
        nickname_to_pokemon[nickname.strip()] = pokemon.strip()

    # Update the faints list with the actual Pokemon names
    faints = [nickname_to_pokemon.get(
        faint.strip(), faint.strip()) for faint in faints]

    for faint in faints:
        # Find the line in which the Pokémon was killed
        killed_line = re.search(
            r"\|move\|(.*?)\|.*?{}(?:\||$)".format(re.escape(faint)), raw_data)

        if killed_line:
            # Extract the killer Pokémon name/nickname from the line
            killer = killed_line.group(1).strip().split(':')[0].strip()

        # Get the actual Pokémon name from the nickname, if applicable
        killer_pokemon = nickname_to_pokemon.get(killer, killer)

        # Increment the kill counter for the killer Pokémon
        if killer_pokemon not in stats:
            stats[killer_pokemon] = {'kills': 0, 'deaths': 0}
        stats[killer_pokemon]['kills'] += 1
        # Find the matching Pokemon in the pokes list
        matching_pokemon = None
        for poke in pokes:
            if faint in poke:
                matching_pokemon = poke
                break

        # If a matching Pokemon is found, increment the death counter
        if matching_pokemon:
            if matching_pokemon not in stats:
                stats[matching_pokemon] = {'kills': 0, 'deaths': 0}
            stats[matching_pokemon]['deaths'] += 1
        else:
            stats[faint] = {'kills': 0, 'deaths': 1}

    # Format and send the kill/death numbers
    message = ""
    for idx, (poke, stat) in enumerate(stats.items(), start=1):
        message += f"Pokemon {idx}: {poke}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")

bot.run("MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00")
