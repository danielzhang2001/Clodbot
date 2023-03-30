import discord
import requests
import re

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message):
    if "clod" in message.content.lower():
        print("Received a message containing 'clod'")
        await message.channel.send("hi")
    await bot.process_commands(message)


async def send_message_every_10_seconds():
    # Replace with the ID of the channel you want the bot to send messages to
    channel = bot.get_channel(CHANNEL_ID)
    while True:
        await channel.send("hi")
        await asyncio.sleep(10)

bot.loop.create_task(send_message_every_10_seconds())

bot.run('MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00')
