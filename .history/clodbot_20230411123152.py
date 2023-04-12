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

    # Find player names
    player_names = re.findall(r"\|j\|☆(.+)", raw_data)

    # Initialize dictionary to store kill/death numbers
    stats = {}

    # Find all Pokemon in the battle
    pokes = re.findall(r"\|poke\|\w+\|(.*?)(?=\||$)", raw_data)

    # Initialize stats dictionary
    for player, poke in pokes:
        key = f"{player}:{poke}"
        if key not in stats:
            stats[key] = {'player': player,
                          'poke': poke, 'kills': 0, 'deaths': 0}

    # Print all Pokémon in the battle
    print("All Pokémon:")
    for idx, poke in enumerate(pokes, start=1):
        print(f"Pokémon {idx}: {poke}")
    print("\n")

    # Initialize stats dictionary
    for poke in pokes:
        if poke not in stats:
            stats[poke] = {'kills': 0, 'deaths': 0}

    # Create a dictionary to store the mapping between nicknames and actual Pokémon names
    nickname_mapping = {}

    # Initialize fainted counters for each player
    player1_fainted = 0
    player2_fainted = 0

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
            # Grab the fainted Pokemon
            fainted_pokemon = re.search(
                r'\|(p\d)a:(.*?)\|', faint).groups()
            fainted_key = f"{fainted_pokemon[0]}:{nickname_mapping.get(fainted_pokemon[1], fainted_pokemon[1])}"

            # Increment the death counter
            if fainted_key in stats:
                stats[fainted_key]['deaths'] += 1
            else:
                stats[fainted_key] = {'player': fainted_pokemon[0],
                                      'poke': fainted_pokemon[1], 'kills': 0, 'deaths': 1}

            # Count fainted Pokémon for each player
            if fainted_pokemon in pokes[:6]:
                player1_fainted += 1
            else:
                player2_fainted += 1

            # Find the lines above the faint line
            index = raw_data.find(faint)
            above_lines = raw_data[:index].split('\n')[::-1]

            # Look at the lines above to find killer Pokemon and update its kills
            for line in above_lines:
                if "|switch|" in line:
                    if (fainted_key.startswith("p1") and "p2a" in line) or (fainted_key.startswith("p2") and "p1a" in line):
                        killer_pokemon = re.search(
                            r'\|(p\d)a:(.*?)\|', line).groups()
                        killer_key = f"{killer_pokemon[0]}:{nickname_mapping.get(killer_pokemon[1], killer_pokemon[1])}"
                        if killer_key in stats:
                            stats[killer_key]['kills'] += 1
                        else:
                            stats[killer_key] = {
                                'player': killer_pokemon[0], 'poke': killer_pokemon[1], 'kills': 1, 'deaths': 0}
                        break

    # Find the winner
    winner = re.search(r"\|win\|(.+)", raw_data).group(1)

    # Calculate the difference
    if winner == player_names[0]:
        difference = f"({player2_fainted}-{player1_fainted})"
    else:
        difference = f"({player1_fainted}-{player2_fainted})"

    # Format and send the kill/death numbers
    message = ""
    message = f"Winner: {winner} {difference}\n\n" + message
    for idx, player_name in enumerate(player_names):
        message += f"{player_name}'s Pokemon:\n\n"
        for idx, (poke, stat) in enumerate(stats.items(), start=1):
            if idx > 6:
                break
            message += f"Pokemon {idx}: {poke}\nKills: {stat['kills']}, Deaths: {stat['deaths']}\n\n"
        stats = dict(list(stats.items())[6:])

    if message:
        await ctx.send(message)
    else:
        await ctx.send("No data found in this replay.")


# Running Discord bot
load_dotenv()
bot_token = os.environ['DISCORD_BOT_TOKEN']
bot.run(bot_token)
