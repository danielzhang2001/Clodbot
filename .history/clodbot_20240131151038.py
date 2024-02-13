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
    # Gives Pokemon set(s) based on Pokemon, Generation, Format and Set provided
    input_str = " ".join(args)
    if "," in input_str:
        pokemons = [p.strip() for p in input_str.split(",")]
        for pokemon in pokemons:
            set_data, sets, url = await GiveSet.fetch_set(pokemon)
            if sets:
                await GiveSet.set_prompt(ctx, pokemon, sets, url)
            else:
                await ctx.send(f'Pokemon "{pokemon}" not found or no sets available.')
    else:
        components = args[0].split() + list(args[1:])
        pokemon = components[0]
        if len(components) == 1:
            pokemon, generation = components
            set_data, sets, url = await GiveSet.fetch_set(pokemon, generation)
            if sets:
                await GiveSet.set_prompt(ctx.pokemon, sets, url)
            else:
                await ctx.send(
                    f'No sets found for "{pokemon}" in Generation "{generation}".'
                )


@bot.event
async def on_interaction(interaction):
    # Handles button functionality for sets for when only a Pokemon parameter with giveset is called
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("set_"):
            parts = custom_id.split("_")
            unique_id, set_index = parts[1], int(parts[2])
            if unique_id in GiveSet.awaiting_response:
                context = GiveSet.awaiting_response[unique_id]
                if interaction.user.id == context["user_id"]:
                    await interaction.response.defer()
                    set_name = context["sets"][set_index]
                    url = context["url"]
                    channel = bot.get_channel(interaction.channel_id)
                    message = await channel.fetch_message(context["message_id"])
                    ctx = await bot.get_context(message)
                    await GiveSet.set_selection(
                        ctx, unique_id, set_index, set_name, url
                    )
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
