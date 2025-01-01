import os
import discord
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

# Target channel name and message content
TARGET_CHANNEL_NAME = "general"
MESSAGE_CONTENT = (
    "Official Trailer Released for Clodbot: https://www.youtube.com/watch?v=CB3H_Uw3y9g"
)
EXCLUDED_SERVER_NAME = "Paradox Parlor Draft League"
SPECIAL_SERVER_NAMES = ["BATTLE FRONTIER GTA", "Clodbot"]

@client.event
async def on_ready():
    print(f"Logged in as: {client.user.name} (ID: {client.user.id})")

    for guild in client.guilds:
        # Skip the excluded server
        if guild.name == EXCLUDED_SERVER_NAME:
            print(f"Skipping server: {guild.name} (ID: {guild.id})")
            continue

        print(f"Processing server: {guild.name} (ID: {guild.id})")

        # Look for the first 'general' channel in the current server
        target_channel = discord.utils.find(
            lambda c: c.name == TARGET_CHANNEL_NAME and isinstance(c, discord.TextChannel),
            guild.text_channels,
        )

        if target_channel:
            try:
                # Use @everyone for special servers
                if guild.name in SPECIAL_SERVER_NAMES:
                    message = f"@everyone {MESSAGE_CONTENT}"
                else:
                    message = MESSAGE_CONTENT

                # Send the message to the 'general' channel
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

# Get the bot token from the .env file
token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    client.run(token)
else:
    print("Token not found. Please check your .env file.")