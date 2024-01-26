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
async def give_set(
    ctx, pokemon: str, generation: str = None, format: str = None, *set: str
):
    # Sends the Pokemon set from Smogon according to the given parameters.
    set_data, sets, url = await GiveSet.fetch_set(
        pokemon, generation, format, " ".join(set)
    )
    if sets:
        await GiveSet.set_prompt(ctx, pokemon, sets, url)
    elif set_data:
        await ctx.send(set_data)
    else:
        await ctx.send(f'Pokemon "{pokemon}" not found.')


@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("set_"):
            set_index = int(custom_id.split("_")[1])

            # Retrieve the original context stored in awaiting_response
            channel_id = interaction.channel_id
            if channel_id in GiveSet.awaiting_response:
                context = GiveSet.awaiting_response[channel_id]

                # Check if the interaction was made by the user who initiated the command
                if interaction.user.id == context["user_id"]:
                    set_name = context["sets"][set_index]
                    url = context["url"]

                    # Extract the ctx from the original message
                    channel = bot.get_channel(channel_id)
                    original_message = await channel.fetch_message(
                        context["message_id"]
                    )
                    ctx = await bot.get_context(original_message)

                    # Now call a method similar to set_selection in giveset.py
                    # Assuming you have a method in GiveSet to handle set selection by index
                    await GiveSet.handle_set_selection_by_index(
                        ctx, set_index, set_name, url
                    )

                    # Cleanup: remove the entry from awaiting_response
                    del GiveSet.awaiting_response[channel_id]
                else:
                    await interaction.response.send_message(
                        "You didn't initiate this command.", ephemeral=True
                    )
            else:
                await interaction.response.send_message(
                    "No active set selection found.", ephemeral=True
                )


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
