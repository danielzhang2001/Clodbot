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
    "Hey guys! Given that we have passed 10,000 unique users of Clodbot across all servers, Discord requires approval for Message Content Intent and our use case just for a prefix of 'Clodbot' doesn't qualify.\n\n"
    "**Therefore, we will be switching to mentioning the bot using @Clod instead of our old prefix to be able to use all commands.** Don't worry, all commands will still function exactly the same as before! Happy Clodding!"
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

        # If no 'general' channel exists, use the first text channel the bot can send messages in
        if target_channel is None:
            target_channel = discord.utils.find(
                lambda c: isinstance(c, discord.TextChannel)
                and c.permissions_for(guild.me).send_messages,
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
            print(f"No usable text channel found in {guild.name}.")

    print("All messages sent. Closing connection.")
    await client.close()

# Get the bot token from the .env file
token = os.getenv("DISCORD_BOT_TOKEN")

if token:
    client.run(token)
else:
    print("Token not found. Please check your .env file.")