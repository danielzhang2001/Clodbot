"""
Functions to check all the servers the bot is running in.
"""

import os
import discord
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    # Prints out all the servers the bot is in.
    print(f"Logged in as: {client.user.name} (ID: {client.user.id})")
    print("Guilds:")
    for guild in client.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    await client.close()


token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    client.run(token)
else:
    print("Token not found. Please check your .env file.")
