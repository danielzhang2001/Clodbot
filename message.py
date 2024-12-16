"""
Sends a message to the 'general' channel of all servers, with specific @everyone handling for certain servers.
"""

import os
import discord
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

TARGET_CHANNEL_NAME = "general"
MESSAGE_CONTENT_STANDARD = (
    "Hello everyone! For those that have been using me (feel free to ignore me if you don't), there have been some major updates! These include:\n\n"
    "**PASSIVE KILL TRACKING**: Instead of the Pokémon on field getting the kill, if the cause of death was passive, the kill instead gets attributed to the initial setter (Stealth Rock, Toxic, etc).\n"
    "**DOUBLES SUPPORT**: I am now able to give accurate information on double battles!\n"
    "**WEEK TRACKING SUPPORT**: I now have the option to update Google Sheets based on week! Hopefully this makes tracking data for Draft Leagues easier!\n\n"
    "Please use **Clodbot, help** to see the list of commands, or visit https://clodbot.com for more information. Thank you, and happy holidays! I'll go back to stalling out OU teams now."
)
MESSAGE_CONTENT_SPECIAL = (
    "Hello @everyone! For those that have been using me (feel free to ignore me if you don't), there have been some major updates! These include:\n\n"
    "**PASSIVE KILL TRACKING**: Instead of the Pokémon on field getting the kill, if the cause of death was passive, the kill instead gets attributed to the initial setter (Stealth Rock, Toxic, etc).\n"
    "**DOUBLES SUPPORT**: I am now able to give accurate information on double battles!\n"
    "**WEEK TRACKING SUPPORT**: I now have the option to update Google Sheets based on week! Hopefully this makes tracking data for Draft Leagues easier!\n\n"
    "Please use **Clodbot, help** to see the list of commands, or visit https://clodbot.com for more information. Thank you, and happy holidays! I'll go back to stalling out OU teams now."
)

SPECIAL_SERVER_NAMES = ["BATTLE FRONTIER GTA", "Clodbot"]


@client.event
async def on_ready():
    print(f"Logged in as: {client.user.name} (ID: {client.user.id})")

    for guild in client.guilds:
        print(f"Processing server: {guild.name} (ID: {guild.id})")

        # Look for the first 'general' channel in the current server
        target_channel = discord.utils.find(
            lambda c: c.name == TARGET_CHANNEL_NAME and isinstance(c, discord.TextChannel),
            guild.text_channels,
        )

        if target_channel:
            try:
                # Use the special message for special servers, otherwise use the standard message
                if guild.name in SPECIAL_SERVER_NAMES:
                    message = MESSAGE_CONTENT_SPECIAL
                else:
                    message = MESSAGE_CONTENT_STANDARD

                # Send the message
                await target_channel.send(message)
                print(f"Message sent to {TARGET_CHANNEL_NAME} in {guild.name}.")
            except discord.Forbidden:
                print(f"Permission denied for channel {TARGET_CHANNEL_NAME} in {guild.name}.")
            except discord.HTTPException as e:
                print(f"Failed to send message to {TARGET_CHANNEL_NAME} in {guild.name}: {e}")
        else:
            print(f"Channel '{TARGET_CHANNEL_NAME}' not found in {guild.name}.")

    print("All messages sent. Closing connection.")
    await client.close()


token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    client.run(token)
else:
    print("Token not found. Please check your .env file.")
