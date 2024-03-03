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


# COMMAND THAT TAKES IN REPLAY LINK AND GOOGLE SHEETS LINK AND STORES REPLAY INFORMATION IN A SPECIFIC SHEET NAME ON THE GOOGLE SHEETS.
# IF SHEET NAME DOES NOT EXIST, CREATE THE SHEET AND STORE INFORMATION IN
# IF SHEET NAME DOES EXIST, USE THAT SHEET AND UPDATE IT WITH INFORMATION


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
        args_list = input_str.split()
        num_pokemon = 1
        if len(args_list) > 1 and args_list[1].isdigit():
            num_pokemon = max(1, int(args_list[1]))
        pokemon_names = random.sample(GiveSet.fetch_cache(), k=num_pokemon)
        pokemon_sets = await GiveSet.fetch_multiset_async(pokemon_names)
        pokemon_data = []
        invalid_pokemon = []
        for name, (sets, url) in zip(pokemon_names, pokemon_sets):
            if sets:
                pokemon_data.append((name, sets, url))
            else:
                invalid_pokemon.append(name)

        if pokemon_data:
            await GiveSet.display_sets(ctx, pokemon_data)
        if invalid_pokemon:
            await ctx.send(
                "No sets found for the requested Pokémon: "
                + ", ".join(invalid_pokemon)
                + "."
            )
    elif "," in input_str:
        parts = input_str.split(",")
        pokemon_requests = []
        for part in parts:
            request_parts = part.strip().split()
            pokemon_requests.append(
                {
                    "name": request_parts[0],
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
        pokemon_sets = await GiveSet.fetch_multiset_async_with_gen_format(
            pokemon_requests
        )
        pokemon_data = []
        for request, result in zip(pokemon_requests, pokemon_sets):
            name, sets, url = result
            if sets:
                pokemon_data.append((name, sets, url))
        if pokemon_data:
            await GiveSet.set_prompt(ctx, pokemon_data)
        else:
            await ctx.send("No sets found for the provided Pokémon.")
    else:
        parts = input_str.split()
        pokemon = parts[0]
        generation = parts[1] if len(parts) > 1 else None
        format = parts[2] if len(parts) > 2 else None
        sets, url = await GiveSet.fetch_set_async(pokemon, generation, format)
        if sets:
            await GiveSet.set_prompt(ctx, [(pokemon, sets, url, generation, format)])
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
                _, sets, url, _, _ = selected_pokemon
                selected_set = sets[set_index]
                await GiveSet.set_selection(
                    interaction, unique_id, set_index, selected_set, url, pokemon
                )


# Running Discord bot
load_dotenv()
bot_token = os.environ["DISCORD_BOT_TOKEN"]
bot.run(bot_token)
