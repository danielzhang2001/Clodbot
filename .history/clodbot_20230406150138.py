import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
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

    # Scrape battle data from the log file of the replay link
    try:
        raw_data = requests.get(replay_link + '.log').text
    except requests.exceptions.RequestException as e:
        await ctx.send(f"An error occurred while fetching the replay data: {e}")
        return

    # Initialize dictionary to store kill/death numbers
    stats = {}

    # Find all Pokemon in the battle
    pokes = re.findall(r"\|poke\|\w+\|(.*?)(?=\||$)", raw_data)

    # Initialize stats dictionary
    for poke in pokes:
        if poke not in stats:
            stats[poke] = {'kills': 0, 'deaths': 0}

    # Create a dictionary to store the mapping between nicknames and actual Pokémon names
    nickname_mapping = {}

    # Find all lines when a Pokemon is switched in
    switches = re.findall(r"\|switch\|.*?:(.*?)\|(.*?)(?=\||$)", raw_data)

    # Replace all nicknames with the actual Pokemon names
    for nickname, pokemon in switches:
        nickname_mapping[nickname.strip()] = pokemon.strip()

    # Find all lines when a Pokemon has fainted
    faints = [line for line in raw_data.split('\n') if 'fnt' in line]

    # Iterate through each fainted line
    for faint in faints:
        if faint:
            fainted_pokemon = re.search(
                r'\|.*?:(.*?)\|', faint).group(1).strip()
            fainted_pokemon = nickname_mapping.get(
                fainted_pokemon, fainted_pokemon)

            # Increment the death counter
            if fainted_pokemon in stats:
                stats[fainted_pokemon]['deaths'] += 1
            else:
                stats[fainted_pokemon] = {'kills': 0, 'deaths': 1}

            # Find the killer Pokemon
            index = raw_data.find(faint)
            above_lines = raw_data[:index].split('\n')[::-1]

            for line in above_lines:
                if "|move|" in line:
                    killer_nickname = re.search(
                        r'\|.*?:(.*?)\|', line).group(1).strip()
                    killer = nickname_mapping.get(
                        killer_nickname, killer_nickname)
                    if killer in stats:
                        stats[killer]['kills'] += 1
                    else:
                        stats[killer] = {'kills': 1, 'deaths': 0}
                    break

    # Format and send the kill/death numbers
    message = ""
    for idx, (poke, stat) in enumerate(stats.items(), start=1):
        message += f"Pokemon {idx}: {poke}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"
    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")

load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)
