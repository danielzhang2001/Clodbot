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
async def give_set(ctx, *args):
    # Gives Pokemon set(s) based on Pokemon, Generation (Optional) and Format (Optional) provided.
    input_str = " ".join(args)
    if "," in input_str:
        pokemons = [p.strip() for p in input_str.split(",")]
        all_pokemon_data = []
        for pokemon in pokemons:
            sets, url = await GiveSet.fetch_set(pokemon)
            if sets:
                all_pokemon_data.append((pokemon, sets, url))
            else:
                await ctx.send(f"No sets found for Pokemon **{pokemon}**.")
    else:
        components = input_str.split()
        if len(components) == 1:
            pokemon = components[0]
            sets, url = await GiveSet.fetch_set(pokemon)
            if sets:
                await GiveSet.set_prompt(ctx, pokemon, sets, url)
            else:
                await ctx.send(f"No sets found for Pokemon **{pokemon}**.")
        elif len(components) == 2:
            pokemon, generation = components
            sets, url = await GiveSet.fetch_set(pokemon, generation)
            if sets:
                await GiveSet.set_prompt(ctx, pokemon, sets, url)
            else:
                await ctx.send(
                    f"No sets found for Pokemon **{pokemon}** in Generation **{generation}**."
                )
        elif len(components) == 3:
            pokemon, generation, format = components
            sets, url = await GiveSet.fetch_set(pokemon, generation, format)
            if sets:
                await GiveSet.set_prompt(ctx, pokemon, sets, url)
            else:
                await ctx.send(
                    f"No sets found for Pokemon **{pokemon}** in Generation **{generation}** with Format **{format}**."
                )
        else:
            await ctx.send(
                "Usage: `Clodbot, giveset [Pokemon]` or `Clodbot, giveset [Pokemon], [Pokemon2]...` or `Clodbot, giveset [Pokemon] [Generation]`."
            )


@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("set_"):
            _, unique_id, pokemon, set_index = custom_id.split("_", 3)
            set_index = int(set_index)  # Convert index back to integer

            if unique_id in GiveSet.awaiting_response:
                context = GiveSet.awaiting_response[unique_id]
                if interaction.user.id == context["user_id"]:
                    await interaction.response.defer()
                    pokemons_data = context["pokemons_data"]
                    # Find the correct pokemon and set data based on interaction
                    for poke_name, sets, url in pokemons_data:
                        if poke_name == pokemon:
                            selected_set = sets[set_index]
                            # Process the selected set further as needed
                            break
                else:
                    await interaction.followup.send(
                        "You didn't initiate this command.", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    "No active set selection found.", ephemeral=True
                )


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
