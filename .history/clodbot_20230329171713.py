import discord

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")


@bot.event
async def on_message(message):
    print(f"Message received: {message.content}")
    await bot.process_commands(message)

bot.run("MTA5MDQ1MDkyNzk5Mjk3NTQ5MQ.GYbHv0.6hnesJZSN_aNZMfraGI_Ssp2E8HSlputZpIU00")
