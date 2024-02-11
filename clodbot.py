"""
The main module for running ClodBot.
"""

# pylint: disable=import-error
import os
import discord  # type: ignore
from discord.ext import commands  # type: ignore
from dotenv import load_dotenv  # type: ignore
import aiohttp
import random
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
    input_str = " ".join(args).strip()
    if input_str.lower() == "random":
        random_pokemon = random.choice(GiveSet.get_pokemon())
        sets, url = await GiveSet.fetch_set(random_pokemon)
        if sets:
            random_set = random.choice(sets)
            await GiveSet.display_set(ctx, random_pokemon, random_set, url)
        else:
            await ctx.send(f"No sets found for **{random_pokemon}**.")
    elif "," in input_str:
        pokemons = [p.strip() for p in input_str.split(",")]
        pokemon_data = []
        not_found = []
        for pokemon in pokemons:
            sets, url = await GiveSet.fetch_set(pokemon)
            if sets:
                pokemon_data.append((pokemon, sets, url))
            else:
                not_found.append(pokemon)
        if pokemon_data:
            await GiveSet.set_prompt(ctx, pokemon_data)
            if not_found:
                await ctx.send(
                    "No sets found for: " + ", ".join([f"**{p}**" for p in not_found])
                )
        else:
            await ctx.send("No sets found for the provided Pokémon.")
    else:
        parts = input_str.split()
        pokemon = parts[0]
        generation = parts[1] if len(parts) > 1 else None
        format = parts[2] if len(parts) > 2 else None
        sets, url = await GiveSet.fetch_set(pokemon, generation, format)
        if sets:
            await GiveSet.set_prompt(ctx, [(pokemon, sets, url)])
        else:
            await ctx.send(
                f"No sets found for **{pokemon}**"
                + (f" in Generation **{generation}**" if generation else "")
                + (f" with Format **{format}**" if format else "")
                + "."
            )


@bot.event
async def on_interaction(interaction):
    # Handles button functionality such that when one is clicked, the appropriate set is displayed.
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("set_"):
            _, unique_id, pokemon, set_index = custom_id.split("_", 3)
            set_index = int(set_index)
            context = GiveSet.awaiting_response.get(unique_id)
            if context and interaction.user.id == context["user_id"]:
                await interaction.response.defer()
                pokemon_data = context["pokemon_data"]
                selected_pokemon = next(
                    (data for data in pokemon_data if data[0] == pokemon), None
                )
                if not selected_pokemon:
                    await interaction.followup.send(
                        "Could not find the selected Pokémon's data.", ephemeral=True
                    )
                    return
                _, sets, url = selected_pokemon
                selected_set = sets[set_index]
                await GiveSet.set_selection(
                    interaction, unique_id, set_index, selected_set, url, pokemon
                )


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
