import discord
import os
from dotenv import load_dotenv
import wavelink

load_dotenv()
bot = discord.Bot()
connections = {}

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name="test", description="test command") # Test command
async def test(ctx: discord.ApplicationContext):
    await ctx.respond("ts pmo heavy...")

@bot.slash_command(name="joinvoice", description="Join a voice channel") # Command to join voice channel
async def joinvoice(ctx: discord.ApplicationContext):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("join a vc unc")
    else: 
        await ctx.respond("okay unc")
    vc = await voice.channel.connect()  # Connect to the voice channel the author is in.
    connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.


@bot.slash_command(name="play", description="Play a song") # Test command
async def test(ctx: discord.ApplicationContext):
    await ctx.respond("playing... (song)")


bot.run(os.getenv('TOKEN'))