import discord
from discord.commands import Option 
from discord.ext import commands
import os
from dotenv import load_dotenv
from pytubefix import YouTube as youtube
from pytubefix.exceptions import VideoUnavailable
import os.path  
import requests 
from youtube_search import YoutubeSearch
import asyncio


load_dotenv()
bot = commands.Bot(command_prefix="$")
connections = {}
global vidid
vid_ids = []
global currentURL
currentURL = "https://www.youtube.com/watch?v=XFkzRNyygfk"
global current
current = "Creep"
global currentArtist
currentArtist = "Radiohead"
global progress
progress = "2:45"
global length
length = "3:30"

def is_valid_youtube_url(url):
    try:
        # Attempt to create a YouTube object
        yt = youtube(url)
        # Check if the video is available
        yt.check_availability()
        return True
    except VideoUnavailable:
        print("The video is unavailable.")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False



class Qadd(discord.ui.View):
    @discord.ui.button(label="Play now", style=discord.ButtonStyle.success)
    async def second_button_callback(self, button, interaction):
        await interaction.response.send_message("Playing song now...")


    @discord.ui.button(label="Add to queue", style=discord.ButtonStyle.secondary)
    async def first_button_callback(self, button, interaction):
        await interaction.response.send_message("Adding song to queue")

class Menu(discord.ui.View):
    # row 0
    @discord.ui.button(label="", emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def last_track(self, button, interaction):
        await interaction.response.send_message("Playing last track..")

    @discord.ui.button(label="", emoji="⏪", style=discord.ButtonStyle.secondary)
    async def back_15(self, button, interaction):
        await interaction.response.send_message("Playing last track..")

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.success)
    async def play_pause(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        if vc and vc.is_playing():
            await interaction.response.send_message("Pausing playback", ephemeral=True)
            vc.pause()
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Resuming playback", ephemeral=True)
        else: 
            await interaction.response.send_message("No audio is playing.", ephemeral=True)
    

    @discord.ui.button(label="", emoji="⏩", style=discord.ButtonStyle.secondary)
    async def forward_15_callback(self, button, interaction):
        await interaction.response.send_message("Playing last track..")

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_track(self, button, interaction):
        await interaction.response.send_message("Playing next track")
    # row 1
    @discord.ui.button(label="", emoji="🔇", style=discord.ButtonStyle.secondary)
    async def mute(self, button, interaction):
        await interaction.response.send_message("Muting playback")
    
    @discord.ui.button(label="", emoji="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, button, interaction):
        await interaction.response.send_message("Shuffling tracks in queue")

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        else:
            await interaction.response.send_message("Ending playback.")
            await vc.disconnect()
            

    @discord.ui.button(label="", emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop(self, button, interaction):
        await interaction.response.send_message("Looping current track")
    
    @discord.ui.button(label="", emoji="🎶", style=discord.ButtonStyle.secondary)
    async def queue(self, button, interaction):
        await interaction.response.send_message("Current audio queue:")


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

async def youtube_autocomplete(ctx: discord.AutocompleteContext):
    search_term = ctx.value.lower()
    try:
        results = await asyncio.to_thread(
            lambda: YoutubeSearch(search_term, max_results=6).to_dict()
        )
        if not results:
            return []
        
        options = []
        for result in results:
            title = result["title"].replace('\n', ' ').strip()
            channel = result["channel"].replace('\n', ' ').strip()
            video_id = result["id"]
            
            if title.casefold().count(channel.casefold()) == 1:
                title = title.casefold().replace(channel.casefold(), '', 1).strip()
                title = title.replace(" - ", '', 1).strip()
            
            formatted_option = f"{channel} - {title}"
            options.append(formatted_option)
     
        return options  # Return list of formatted options
    
    except Exception as e:
        print(f"Error during YouTube search: {e}")
        return []



@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")



@bot.slash_command(name="menu", description="bring up the playback menu.")
async def embed_example(interaction: discord.Interaction):
    # Create the embed
    embed = discord.Embed(
        title="Now Playing",
        color=discord.Colour.blurple(),
    )
    embed.set_thumbnail(url="https://cdns-images.dzcdn.net/images/cover/f08424290260e58c6d76275253b316fd/1900x1900-000000-80-0-0.jpg")
    
    # Format the URL with custom display text
    embed.add_field(name="Track", value=f"[{current}]({currentURL})", inline=False)
    embed.add_field(name="Artist", value=f"{currentArtist}", inline=False)
    percentage = None
    embed.add_field(name="Progress", value=f"{progress} |⎯⎯⎯⎯⎯⎯⎯⎯■⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯| {length}", inline=False)

    view = Menu()
    await interaction.response.send_message(embed=embed, view=view)

    

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

@bot.slash_command(name="forceplay", description="Forecefully play a song for testing purposes.")
async def joinvoice(ctx: discord.ApplicationContext):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Join a VC first, unc!")
        return None
    else: 
        pass

        vc = connections.get(ctx.guild.id)

        audio_file = "Radiohead - Creep.wav"
        
        if vc is None:
            vc = await voice.channel.connect()
            connections.update({ctx.guild.id: vc})

        if not os.path.isfile(audio_file):
            await ctx.respond(f"Audio file not found at {audio_file}")
            return

        if not vc.is_playing():
            print("Joining vc...")
            await ctx.respond("Playing your song now")
            audio_source = discord.FFmpegPCMAudio(audio_file)

            vc.play(audio_source, after=lambda e: print(f'Audio finished with error: {e}'))
        else:
            await ctx.respond("A song is already playing.", view=Qadd()) # Send a message with our View class that contains the button

@bot.slash_command(name="play", description="Play a song by YouTube name.")
async def play(
    ctx: discord.ApplicationContext,
    song: Option(str, "Choose a song", autocomplete=youtube_autocomplete)
):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Join a VC first, unc!")
        return None
    else:
        pass
    
        vc = connections.get(ctx.guild.id)

        global result
        vidid = result.get(song, "Unknown ID")  # Store the selected video ID
        await ctx.respond(f"You selected: {song} (Video ID: {vidid})")  

        url = f"https://youtube.com/watch/{vidid}"
        await ctx.respond(url)

        yt = youtube(url)

        audio = yt.streams.filter(only_audio=True).order_by('abr').last()
        
        
        path = os.path.join(os.getcwd(), "audio")

        out_file = audio.download(output_path=path)

        base, ext = os.path.splitext(out_file)
        new_file = base + '.wav'
        if os.path.isfile(new_file) == True:
            await ctx.respond("file already exists, reusing file...")
        if os.path.isfile(new_file) == False:
            os.rename(out_file, new_file)

    


@bot.slash_command(name="playurl", description="Play a song by YouTube URL")
async def forceplay(ctx: discord.ApplicationContext):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Join a VC first, unc!")
        return None
    else: 
        pass

        vc = connections.get(ctx.guild.id)
        
        if is_valid_youtube_url(url):
            await ctx.respond("The URL is valid")
        else:
            await ctx.respond("The URL is invalid, or connection to youtube servers failed.")
        
        yt = youtube(url)

        audio = yt.streams.filter(only_audio=True).order_by('abr').last()
        
        path = os.path.join(os.getcwd(), "audio")

        out_file = audio.download(output_path=path)

        base, ext = os.path.splitext(out_file)
        new_file = base + '.wav'
        if os.path.isfile(new_file) == True:
            await ctx.respond("file already exists, reusing file...")
        if os.path.isfile(new_file) == False:
            os.rename(out_file, new_file)
        
        if vc is None:
            vc = await voice.channel.connect()
            connections.update({ctx.guild.id: vc})

        audio_file = new_file
        if not os.path.isfile(audio_file):
            await ctx.respond(f"Audio file not found at {audio_file}")
            return

        if not vc.is_playing():
            print("Joining vc...")
            await ctx.respond("Playing your song now")
            audio_source = discord.FFmpegPCMAudio(audio_file)
            vc.play(audio_source, after=lambda e: print(f'Audio finished with error: {e}'))
        else:
            async def button(ctx):
                await ctx.respond("A song is already playing.", view=Qadd()) # Send a message with our View class that contains the button


@bot.slash_command(name="qtest", description="For testing the queue system")
async def button(ctx):
    await ctx.respond("A song is already playing.", view=Qadd()) # Send a message with our View class that contains the button


@bot.slash_command(name="stop", description="Stop playback")
async def stop(ctx: discord.ApplicationContext):
    vc = connections.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.stop()
        await ctx.respond("Stopping playback")
    else:
        await ctx.respond("No audio is playing.")

@bot.slash_command(name="pause", description="Pause playback")
async def pause(ctx: discord.ApplicationContext):
    vc = connections.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.pause()
        await ctx.respond("Pausing playback")
    else:
        await ctx.respond("No audio is playing.")

@bot.slash_command(name="resume", description="Resume playback")
async def pause(ctx: discord.ApplicationContext):
    vc = connections.get(ctx.guild.id)
    if vc and vc.is_playing():
        vc.play()
        await ctx.respond("Resuming playback.")
    else:
        await ctx.respond("No audio is playing.")

@bot.slash_command(name="droptest", description="ts")
async def droptest(ctx):
    await ctx.respond("Dropdown Menu Test", view=dropTest())

@bot.slash_command(name="validate", description="Validate a youtube URL")
async def add(ctx, url: discord.Option(str)):
    if is_valid_youtube_url(url):
        await ctx.respond("The URL is valid")
    else:
        await ctx.respond("The URL is invalid or the video is unavailable.")

bot.run(os.getenv('TOKEN'))
#did i fix it?
