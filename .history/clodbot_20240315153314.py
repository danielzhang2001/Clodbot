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
import requests

intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.message_content = True

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)

gen_dict = {
    "gen1": "rb",
    "gen2": "gs",
    "gen3": "rs",
    "gen4": "dp",
    "gen5": "bw",
    "gen6": "xy",
    "gen7": "sm",
    "gen8": "ss",
    "gen9": "sv",
}


@bot.event
async def on_ready():
    # Print a message when the bot connects to Discord.
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_interaction(interaction):
    # Displays set information and changes button style if necessary when a button is clicked.
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        parts = custom_id.split("_")
        pokemon = parts[0]
        generation = parts[1] if parts[1] != "none" else None
        format = parts[2] if parts[2] != "none" else None
        set_name = "_".join(parts[3:])
        await interaction.response.defer()
        await GiveSet.set_selection(interaction, pokemon, generation, format, set_name)


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
    if input_str.startswith("random"):
        await GiveSet.fetch_random_sets(ctx, input_str)
    elif "," in input_str:
        parts = input_str.split(",")
        pokemon_requests = []
        for part in parts:
            request_parts = part.strip().split()
            pokemon_requests.append(
                {
                    "pokemon": request_parts[0],
                    "generation": (
                        request_parts[1]
                        if len(request_parts) > 1 and request_parts[1].startswith("gen")
                        else None
                    ),
                    "format": (
                        " ".join(request_parts[2:])
                        if len(request_parts) > 2
                        else (
                            " ".join(request_parts[1:])
                            if len(request_parts) > 1
                            and not request_parts[1].startswith("gen")
                            else None
                        )
                    ),
                }
            )
        pokemon_sets = await GiveSet.fetch_multiset_async(pokemon_requests)
        pokemon_data = []
        for request, (name, sets, url) in zip(pokemon_requests, pokemon_sets):
            generation = request["generation"]
            format = request["format"]
            if sets:
                pokemon_data.append((name, sets, url, generation, format))
        if pokemon_data:
            await GiveSet.set_prompt(ctx, pokemon_data)
        else:
            await ctx.send("No sets found for the provided Pokémon.")
    else:
        parts = input_str.split()
        pokemon = parts[0]
        generation = parts[1] if len(parts) > 1 else None
        format = parts[2] if len(parts) > 2 else None
        await GiveSet.set_prompt(ctx, pokemon, generation, format)


# COMMAND THAT TAKES IN REPLAY LINK AND GOOGLE SHEETS LINK AND STORES REPLAY INFORMATION IN A SPECIFIC SHEET NAME ON THE GOOGLE SHEETS.
# IF SHEET NAME DOES NOT EXIST, CREATE THE SHEET AND STORE INFORMATION IN
# IF SHEET NAME DOES EXIST, USE THAT SHEET AND UPDATE IT WITH INFORMATION

# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
