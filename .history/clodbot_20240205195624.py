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
        if all_pokemon_data:
            await GiveSet.set_prompt(ctx, all_pokemon_data)
        else:
            await ctx.send("No sets found for the provided Pokémon.")
    else:
        # Handling for single Pokemon, with optional generation and format, remains unchanged
        components = input_str.split()
        if len(components) == 1:
            pokemon = components[0]
        elif len(components) >= 2:
            pokemon = components[0]
            generation = components[1] if len(components) > 1 else None
            format = components[2] if len(components) > 2 else None
        sets, url = await GiveSet.fetch_set(
            pokemon,
            generation if "generation" in locals() else None,
            format if "format" in locals() else None,
        )
        if sets:
            await GiveSet.set_prompt(
                ctx, [(pokemon, sets, url)]
            )  # Modified to fit the new set_prompt structure
        else:
            await ctx.send(
                f"No sets found for {pokemon}"
                + (f" in Generation {generation}" if "generation" in locals() else "")
                + (f" with Format {format}" if "format" in locals() else "")
                + "."
            )


@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data["custom_id"]
        if custom_id.startswith("set_"):
            _, unique_id, pokemon, set_index = custom_id.split("_", 3)
            set_index = int(set_index)  # Convert index back to integer

            context = GiveSet.awaiting_response.get(unique_id)
            if context and interaction.user.id == context["user_id"]:
                await interaction.response.defer()
                pokemons_data = context["pokemons_data"]

                selected_pokemon_data = next(
                    (data for data in pokemons_data if data[0] == pokemon), None
                )
                if not selected_pokemon_data:
                    await interaction.followup.send(
                        "Could not find the selected Pokémon's data.", ephemeral=True
                    )
                    return

                _, sets, url = selected_pokemon_data
                selected_set = sets[set_index]

                # Call set_selection with the correct parameters
                await GiveSet.set_selection(
                    interaction, unique_id, set_index, selected_set, url
                )


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
