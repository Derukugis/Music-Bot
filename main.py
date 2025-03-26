import discord
import os
from dotenv import load_dotenv
from pytubefix import YouTube as youtube
import os

load_dotenv()
bot = discord.Bot()
connections = {}


class dropTest(discord.ui.View):
    @discord.ui.select( # the decorator that lets you specify the properties of the select menu
        placeholder = "ts is a test", # the placeholder text that will be displayed if nothing is selected
        min_values = 1, # the minimum number of values that must be selected by the users
        max_values = 1, # the maximum number of values that can be selected by the users
        options = [ # the list of options from which users can choose, a required field
            discord.SelectOption(
                label="1",
                description="Option 1"
            ),
            discord.SelectOption(
                label="2",
                description="Option 2"
            ),
            discord.SelectOption(
                label="3",
                description="Option 3"
            )
        ]
    )
    async def select_callback(self, select, interaction): # the function called when the user is done selecting options
        if select.values[0] == "1":
            await interaction.response.send_message(f"option {select.values[0]} does not pmo")
        else:
            await interaction.response.send_message(f"option {select.values[0]} pmo")


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

@bot.slash_command(name="play", description="Play a song")
async def add(ctx, play: discord.Option(int)):
    async def play(ctx: discord.ApplicationContext):
        voice = ctx.author.voice
        if not voice:
            await ctx.respond("Join a VC first, unc!")
        else:
            await ctx.respond("Playing your song now...")

            vc = connections.get(ctx.guild.id)

            if vc is None:
                vc = await voice.channel.connect()
                connections.update({ctx.guild.id: vc})

            audio_file = "head.wav"
            if not os.path.isfile(audio_file):
                await ctx.respond(f"Audio file not found at {audio_file}")
                return

            audio_source = discord.FFmpegPCMAudio(audio_file)

            if not vc.is_playing():
                print("Joining vc...")
                vc.play(audio_source, after=lambda e: print(f'Audio finished with error: {e}'))
            else:
                await ctx.respond("The bot is already playing audio!")

@bot.slash_command(name="playurl", description="Play a song by YouTube URL")
async def add(ctx, url: discord.Option(str)):
        voice = ctx.author.voice
        if not voice:
            await ctx.respond("Join a VC first, unc!")
        else:
            await ctx.respond("Playing your song now...")

            vc = connections.get(ctx.guild.id)
            
            yt = youtube(url)
            
            audio = yt.streams.filter(only_audio=True).order_by('abr').last()
            
            path = os.path.join(os.getcwd(), "audio")

            out_file = audio.download(output_path=path)

            base, ext = os.path.splitext(out_file)
            new_file = base + '.wav'
            os.rename(out_file, new_file)
    
            if vc is None:
                vc = await voice.channel.connect()
                connections.update({ctx.guild.id: vc})

            audio_file = new_file
            if not os.path.isfile(audio_file):
                await ctx.respond(f"Audio file not found at {audio_file}")
                return

            audio_source = discord.FFmpegPCMAudio(audio_file)

            if not vc.is_playing():
                print("Joining vc...")
                vc.play(audio_source, after=lambda e: print(f'Audio finished with error: {e}'))
            else:
                await ctx.respond("The bot is already playing audio!")

@bot.slash_command(name="stop", description="Stop the music")
async def stop(ctx: discord.ApplicationContext):
    vc = connections.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.stop()
        await ctx.respond("Stopped the audio.")
    else:
        await ctx.respond("No audio is playing!")

@bot.slash_command(name="droptest", description="ts")
async def droptest(ctx):
    await ctx.respond("Dropdown Menu Test", view=dropTest())


bot.run(os.getenv('TOKEN'))