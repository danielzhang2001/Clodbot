import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!")


@bot.event
async def on_message(message):
    print(message.content)
    await bot.process_commands(message)

bot.run("MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00")
