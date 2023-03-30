import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="Clodbot, ", intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message):
    print("Message received")
    print(f"Message content: {message.content}")
    if "clod" in message.content.lower():
        print("Received a message containing 'clod'")
        await message.channel.send("hi")
    await bot.process_commands(message)

bot.run('MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00')
