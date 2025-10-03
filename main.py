import discord
from discord.commands import Option 
from discord.ext import commands
import os
from dotenv import load_dotenv
from pytubefix import YouTube as youtube, Playlist
from pytubefix.exceptions import VideoUnavailable
import os.path  
import requests 
from youtube_search import YoutubeSearch
import asyncio
import time
import datetime


load_dotenv()
bot = commands.Bot(command_prefix="$")
connections = {}

music_queues = {}  
current_songs = {}  
song_start_times = {} 
song_durations = {}
song_history = {}
loop_modes = {}

video_search_cache = {}

def seek_to_position(guild_id, target_seconds):
    if guild_id not in song_start_times:
        return False
    
    total_duration = song_durations.get(guild_id, 0)
    if target_seconds < 0:
        target_seconds = 0
    elif target_seconds >= total_duration and total_duration > 0:
        target_seconds = total_duration - 1
    
    song_start_times[guild_id] = time.time() - target_seconds
    return True

def seconds_to_mmss(seconds):
    if seconds is None or seconds < 0:
        return "0:00"
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes}:{seconds:02d}"

def get_song_progress(guild_id):
    if guild_id not in song_start_times:
        return 0
    
    start_time = song_start_times[guild_id]
    current_time = time.time()
    return current_time - start_time

def create_progress_bar(current_seconds, total_seconds, bar_length=20):
    if total_seconds <= 0:
        return "⎯" * bar_length
    
    progress_ratio = min(current_seconds / total_seconds, 1.0)
    filled_length = int(bar_length * progress_ratio)
    
    bar = "■" * filled_length + "⎯" * (bar_length - filled_length)
    return bar

def create_song_dict(video_url, title=None, artist=None, thumbnail=None, duration=None):
    try:
        yt = youtube(video_url)
        duration_seconds = yt.length if yt.length else 0
        return {
            'url': video_url,
            'title': title or yt.title,
            'artist': artist or yt.author,
            'thumbnail': thumbnail or yt.thumbnail_url,
            'duration': duration or seconds_to_mmss(duration_seconds),
            'duration_seconds': duration_seconds,
            'video_id': yt.video_id
        }
    except Exception as e:
        return {
            'url': video_url,
            'title': title or "Unknown Title",
            'artist': artist or "Unknown Artist", 
            'thumbnail': thumbnail or "",
            'duration': duration or "Unknown",
            'duration_seconds': 0,
            'video_id': video_url.split('v=')[-1] if 'v=' in video_url else ""
        }

def get_or_create_history(guild_id):
    if guild_id not in song_history:
        song_history[guild_id] = []
    return song_history[guild_id]

def get_loop_mode(guild_id):
    return loop_modes.get(guild_id, "off")

def set_loop_mode(guild_id, mode):
    if mode in ["off", "song", "queue"]:
        loop_modes[guild_id] = mode
        return True
    return False

def add_to_history(guild_id, song_dict):
    history = get_or_create_history(guild_id)
    history.insert(0, song_dict)
    if len(history) > 50:  # Keep only last 50 songs
        history.pop()

def get_previous_song(guild_id):
    history = get_or_create_history(guild_id)
    if len(history) > 1:  
        return history.pop(1)
    return None

def get_or_create_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = []
    return music_queues[guild_id]

def add_to_queue(guild_id, song_dict):
    queue = get_or_create_queue(guild_id)
    queue.append(song_dict)
    return len(queue)

def get_next_song(guild_id):
    queue = get_or_create_queue(guild_id)
    if queue:
        return queue.pop(0)
    return None

def set_current_song(guild_id, song_dict):
    if guild_id in current_songs:
        add_to_history(guild_id, current_songs[guild_id])
    
    current_songs[guild_id] = song_dict
    song_start_times[guild_id] = time.time()
    song_durations[guild_id] = song_dict.get('duration_seconds', 0)

def get_current_song(guild_id):
    return current_songs.get(guild_id)

def is_valid_youtube_url(url):
    try:
        yt = youtube(url)
        yt.check_availability()
        return True
    except VideoUnavailable:
        return False
    except Exception as e:
        return False

def is_valid_youtube_playlist_url(url):
    try:
        if 'playlist?list=' in url or 'list=' in url:
            playlist = Playlist(url)
            _ = playlist.title
            return True
        return False
    except Exception as e:
        return False

def extract_playlist_info(url):
    try:
        playlist = Playlist(url)
        return {
            'title': playlist.title,
            'owner': playlist.owner,
            'length': len(playlist.video_urls),
            'videos': playlist.video_urls
        }
    except Exception as e:
        return None



class Qadd(discord.ui.View):
    def __init__(self, song_dict=None, guild_id=None):
        super().__init__()
        self.song_dict = song_dict
        self.guild_id = guild_id

    @discord.ui.button(label="Play now", style=discord.ButtonStyle.success)
    async def play_now_callback(self, button, interaction):
        if not self.song_dict or not self.guild_id:
            await interaction.response.send_message("Error: Missing song information", ephemeral=True)
            return
            
        guild = interaction.guild
        vc = connections.get(guild.id)
        
        if vc is None:
            await interaction.response.send_message("Bot is not connected to voice.", ephemeral=True)
            return
        
        if vc.is_playing() or vc.is_paused():
            vc.stop()
        
        queue = get_or_create_queue(self.guild_id)
        queue.insert(0, self.song_dict)
        
        class DummyCtx:
            def __init__(self, guild):
                self.guild = guild
            async def send(self, content):
                pass
        
        dummy_ctx = DummyCtx(guild)
        await play_next_song(dummy_ctx, vc)
        
        await interaction.response.send_message(f"**{self.song_dict['title']}** will play next!")

    @discord.ui.button(label="Add to queue", style=discord.ButtonStyle.secondary)
    async def add_to_queue_callback(self, button, interaction):
        if not self.song_dict or not self.guild_id:
            await interaction.response.send_message("Error: Missing song information", ephemeral=True)
            return
            
        queue_position = add_to_queue(self.guild_id, self.song_dict)
        await interaction.response.send_message(f"Added **{self.song_dict['title']}** to queue at position {queue_position}")

class Menu(discord.ui.View):
    # row 0
    @discord.ui.button(label="", emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def last_track(self, button, interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        
        # Get previous song from history
        previous_song = get_previous_song(guild.id)
        if previous_song:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            
            queue = get_or_create_queue(guild.id)
            queue.insert(0, previous_song)
            
            class DummyCtx:
                def __init__(self, guild):
                    self.guild = guild
                async def send(self, content):
                    pass
            
            dummy_ctx = DummyCtx(guild)
            await play_next_song(dummy_ctx, vc)
            
            await interaction.response.send_message(f"Playing previous track: **{previous_song['title']}**", ephemeral=True)
        else:
            await interaction.response.send_message("No previous track available in history", ephemeral=True)

    @discord.ui.button(label="", emoji="⏪", style=discord.ButtonStyle.secondary)
    async def back_15(self, button, interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        
        current_song = get_current_song(guild.id)
        if not current_song or not vc.is_playing():
            await interaction.response.send_message("No audio currently playing", ephemeral=True)
            return
        
        current_progress = get_song_progress(guild.id)
        new_position = max(0, current_progress - 15)
        
        if seek_to_position(guild.id, new_position):
            await interaction.response.send_message("Rewound 15 seconds", ephemeral=True)
        else:
            await interaction.response.send_message("Unable to rewind", ephemeral=True)

    @discord.ui.button(label="", emoji="⏯️", style=discord.ButtonStyle.success)
    async def play_pause(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        if vc and vc.is_playing():
            await interaction.response.send_message("Paused playback", ephemeral=True)
            vc.pause()
        elif vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Resumed playback", ephemeral=True)
        else: 
            await interaction.response.send_message("No audio is playing.", ephemeral=True)
    

    @discord.ui.button(label="", emoji="⏩", style=discord.ButtonStyle.secondary)
    async def forward_15_callback(self, button, interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        
        current_song = get_current_song(guild.id)
        if not current_song or not vc.is_playing():
            await interaction.response.send_message("No audio currently playing", ephemeral=True)
            return
        
        current_progress = get_song_progress(guild.id)
        total_duration = song_durations.get(guild.id, 0)
        new_position = current_progress + 15
        
        if total_duration > 0 and new_position >= total_duration:
            await interaction.response.send_message("Cannot fast-forward beyond song end", ephemeral=True)
            return
        
        if seek_to_position(guild.id, new_position):
            await interaction.response.send_message("Fast-forwarded 15 seconds", ephemeral=True)
        else:
            await interaction.response.send_message("Unable to fast-forward", ephemeral=True)

    @discord.ui.button(label="", emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def next_track(self, button, interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        
        queue = get_or_create_queue(guild.id)
        if not queue:
            await interaction.response.send_message("No more songs in queue", ephemeral=True)
            return
        
        if vc.is_playing() or vc.is_paused():
            vc.stop()
            await interaction.response.send_message("Skipped to next track", ephemeral=True)
            
            class DummyCtx:
                def __init__(self, guild):
                    self.guild = guild
                async def send(self, content):
                    await interaction.followup.send(content)
            
            dummy_ctx = DummyCtx(guild)
            await play_next_song(dummy_ctx, vc)
        else:
            try:
                class DummyCtx:
                    def __init__(self, guild):
                        self.guild = guild
                    async def send(self, content):
                        await interaction.followup.send(content)
                
                dummy_ctx = DummyCtx(guild)
                await play_next_song(dummy_ctx, vc)
                await interaction.response.send_message("Started next track", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Error playing next track: {str(e)}", ephemeral=True)

    # row 1
    @discord.ui.button(label="", emoji="🔇", style=discord.ButtonStyle.secondary)
    async def mute(self, button, interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        
        if vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Muted (paused) playback", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing to mute", ephemeral=True)
    
    @discord.ui.button(label="", emoji="🔀", style=discord.ButtonStyle.secondary)
    async def shuffle(self, button, interaction):
        import random
        guild_id = interaction.guild.id
        queue = get_or_create_queue(guild_id)
        
        if len(queue) < 2:
            await interaction.response.send_message("Need at least 2 songs in queue to shuffle", ephemeral=True)
            return
        
        random.shuffle(queue)
        music_queues[guild_id] = queue
        
        await interaction.response.send_message(f"Shuffled {len(queue)} songs in queue", ephemeral=True)

    @discord.ui.button(label="", emoji="⏹️", style=discord.ButtonStyle.danger)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        guild = interaction.guild
        vc = connections.get(guild.id)
        if vc is None:
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return
        else:
            if guild.id in music_queues:
                music_queues[guild.id].clear()
            if guild.id in current_songs:
                del current_songs[guild.id]
            if guild.id in song_history:
                song_history[guild.id].clear()
            if guild.id in loop_modes:
                del loop_modes[guild.id]
            
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            
            await interaction.response.send_message("Stopped playback and cleared queue & history.")
            await vc.disconnect()
            

    @discord.ui.button(label="", emoji="🔁", style=discord.ButtonStyle.secondary)
    async def loop(self, button, interaction):
        guild_id = interaction.guild.id
        current_mode = get_loop_mode(guild_id)
        
        if current_mode == "off":
            new_mode = "song"
            description = "Loop: Current Song"
        elif current_mode == "song":
            new_mode = "queue"
            description = "Loop: Queue"
        else:  # queue
            new_mode = "off"
            description = "Loop: Off"
        
        set_loop_mode(guild_id, new_mode)
        await interaction.response.send_message(f"{description}", ephemeral=True)
    
    @discord.ui.button(label="", emoji="🎶", style=discord.ButtonStyle.secondary)
    async def queue(self, button, interaction):
        guild_id = interaction.guild.id
        queue = get_or_create_queue(guild_id)
        current_song = get_current_song(guild_id)
        
        embed = discord.Embed(title="🎶 Music Queue", color=discord.Colour.blue())
        
        if current_song:
            embed.add_field(
                name="🎵 Currently Playing",
                value=f"**{current_song['title']}** by {current_song['artist']}",
                inline=False
            )
        
        if queue:
            queue_text = ""
            for i, song in enumerate(queue[:5]):  # Show first 5 songs
                queue_text += f"{i+1}. **{song['title']}** by {song['artist']}\n"
            
            if len(queue) > 5:
                queue_text += f"... and {len(queue) - 5} more songs"
                
            embed.add_field(name="Up Next", value=queue_text, inline=False)
            embed.set_footer(text=f"Total songs in queue: {len(queue)}")
        else:
            embed.add_field(name="Queue", value="Queue is empty", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def youtube_autocomplete(ctx: discord.AutocompleteContext):
    search_term = ctx.value.lower()
    try:
        results = await asyncio.to_thread(
            lambda: YoutubeSearch(search_term, max_results=6).to_dict()
        )
        if not results:
            return []

        global video_search_cache
        video_search_cache = {} 

        options = []
        for result in results:
            title = result["title"].replace('\n', ' ').strip()
            channel = result["channel"].replace('\n', ' ').strip()
            video_id = result["id"]

            formatted_option = f"{channel} - {title}"
            if len(formatted_option) > 95:  
                max_title_length = 95 - len(channel) - 3 
                if max_title_length > 10:  # Ensure minimum readable title
                    title = title[:max_title_length-3] + "..."
                    formatted_option = f"{channel} - {title}"
                else:
                    # If channel name is too long, truncate it instead
                    channel = channel[:40] + "..."
                    title = title[:50] + "..." if len(title) > 50 else title
                    formatted_option = f"{channel} - {title}"
            
            # Final safety check - ensure it's under 100 characters
            if len(formatted_option) > 100:
                formatted_option = formatted_option[:97] + "..."
            
            video_search_cache[formatted_option] = video_id
            options.append(formatted_option)

        return options
    except Exception as e:
        return []


@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")



@bot.slash_command(name="menu", description="bring up the playback menu.")
async def embed_example(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    current_song = get_current_song(guild_id)
    
    embed = discord.Embed(
        title="🎵 Now Playing",
        color=discord.Colour.blurple(),
    )
    
    if current_song:
        embed.set_thumbnail(url=current_song.get('thumbnail', 'https://cdns-images.dzcdn.net/images/cover/f08424290260e58c6d76275253b316fd/1900x1900-000000-80-0-0.jpg'))
        embed.add_field(name="Track", value=f"[{current_song['title']}]({current_song['url']})", inline=False)
        embed.add_field(name="Artist", value=f"{current_song['artist']}", inline=False)
        
        current_progress_seconds = get_song_progress(guild_id)
        total_seconds = song_durations.get(guild_id, 0)
        
        progress_text = seconds_to_mmss(current_progress_seconds)
        duration_text = current_song.get('duration', 'Unknown')
        progress_bar = create_progress_bar(current_progress_seconds, total_seconds)
        
        embed.add_field(name="Progress", value=f"{progress_text} |{progress_bar}| {duration_text}", inline=False)
        
        loop_mode = get_loop_mode(guild_id)
        if loop_mode == "song":
            embed.add_field(name="Loop", value="🔂 Current Song", inline=True)
        elif loop_mode == "queue":
            embed.add_field(name="Loop", value="🔁 Queue", inline=True)
        else:
            embed.add_field(name="Loop", value="➡️ Off", inline=True)
        
        queue = get_or_create_queue(guild_id)
        queue_count = len(queue)
        if queue_count > 0:
            next_song = queue[0] if queue else None
            if next_song:
                embed.add_field(name="Up Next", value=f"{next_song['title']} by {next_song['artist']}", inline=False)
            embed.add_field(name="Queue", value=f"{queue_count} song(s) remaining", inline=True)
        else:
            embed.add_field(name="Queue", value="Queue is empty", inline=True)
    else:
        embed.set_thumbnail(url="https://cdns-images.dzcdn.net/images/cover/f08424290260e58c6d76275253b316fd/1900x1900-000000-80-0-0.jpg")
        embed.add_field(name="Status", value="No song currently playing", inline=False)
        embed.add_field(name="Queue", value="Use `/play` or `/playlist` to start listening!", inline=False)

    view = Menu()
    await interaction.response.send_message(embed=embed, view=view)


@bot.slash_command(name="joinvoice", description="Join a voice channel")
async def joinvoice(ctx: discord.ApplicationContext):
    await ctx.defer() 

    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Please join a voice channel first!")
        return
    
    vc = await voice.channel.connect()
    connections.update({ctx.guild.id: vc})
    
    await ctx.respond(f"Joined **{voice.channel.name}**")


@bot.slash_command(name="forceplay", description="Force play a test audio file.")
async def forceplay(ctx: discord.ApplicationContext):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Please join a voice channel first!")
        return None

    vc = connections.get(ctx.guild.id)

    audio_file = "audio/Radiohead - Creep.flac"
    
    if vc is None:
        vc = await voice.channel.connect()
        connections.update({ctx.guild.id: vc})

    if not os.path.isfile(audio_file):
        await ctx.respond(f"Audio file not found at {audio_file}")
        return

    if not vc.is_playing():
        await ctx.respond("Playing test audio")
        audio_source = discord.FFmpegPCMAudio(audio_file)

        vc.play(audio_source, after=lambda e: print(f'Player finished') if not e else print(f'Player error: {e}'))
    else:
        test_song = {
            'url': 'https://www.youtube.com/watch?v=XFkzRNyygfk',
            'title': 'Radiohead - Creep',
            'artist': 'Radiohead',
            'thumbnail': 'https://cdns-images.dzcdn.net/images/cover/f08424290260e58c6d76275253b316fd/1900x1900-000000-80-0-0.jpg',
            'duration': '3:30',
            'video_id': 'XFkzRNyygfk'
        }
        view = Qadd(test_song, ctx.guild.id)
        await ctx.respond("A song is already playing.", view=view)

@bot.slash_command(name="play", description="Play a song by YouTube name.")
async def play(
    ctx: discord.ApplicationContext,
    song: str = Option(description="Choose a song", autocomplete=youtube_autocomplete)
):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Please join a voice channel first!")
        return

    vc = connections.get(ctx.guild.id)

    global video_search_cache
    vidid = video_search_cache.get(song)

    if not vidid:
        await ctx.respond("Couldn't find the selected song.")
        return

    url = f"https://youtube.com/watch?v={vidid}"
    
    # Create song dictionary with proper metadata
    song_dict = create_song_dict(url)
    
    await ctx.respond(f"**{song_dict['title']}** by {song_dict['artist']}")

    if vc is None:
        vc = await voice.channel.connect()
        connections.update({ctx.guild.id: vc})

    # Check if something is already playing
    if vc.is_playing():
        queue_position = add_to_queue(ctx.guild.id, song_dict)
        view = Qadd(song_dict, ctx.guild.id)
        await ctx.send(f"Added to queue at position {queue_position}.", view=view)
        return

    # Set as current song and play immediately
    set_current_song(ctx.guild.id, song_dict)
    
    try:
        yt = youtube(url)
        audio = yt.streams.filter(only_audio=True).order_by('abr').last()
        
        path = os.path.join(os.getcwd(), "audio")
        out_file = audio.download(output_path=path)

        base, ext = os.path.splitext(out_file)
        new_file = base + '.flac'

        if os.path.isfile(new_file):
            await ctx.send("Using cached audio file...")
        else:
            os.rename(out_file, new_file)

        if not os.path.isfile(new_file):
            await ctx.send(f"Unable to download audio file")
            return

        # Play the audio with auto-queue functionality
        await ctx.send("Playing now!")
        audio_source = discord.FFmpegPCMAudio(new_file)
        
        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            # Auto-play next song when current finishes - fix event loop issue
            def schedule_next():
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.create_task(play_next_song(ctx, vc))
                except RuntimeError:
                    pass
            
            schedule_next()
        
        vc.play(audio_source, after=after_playing)
        
    except Exception as e:
        await ctx.send(f"Error playing song: Unable to play this track")


@bot.slash_command(name="playurl", description="Play a song by YouTube URL")
async def playurl(ctx: discord.ApplicationContext, url: str = Option(description="YouTube URL to play")):
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Please join a voice channel first!")
        return

    vc = connections.get(ctx.guild.id)
    
    if not is_valid_youtube_url(url):
        await ctx.respond("Invalid YouTube URL or video unavailable")
        return
    
    await ctx.respond("Valid YouTube URL, processing...")
    
    # Create song dictionary with proper metadata
    song_dict = create_song_dict(url)
    
    if vc is None:
        vc = await voice.channel.connect()
        connections.update({ctx.guild.id: vc})

    # Check if something is already playing
    if vc.is_playing():
        queue_position = add_to_queue(ctx.guild.id, song_dict)
        view = Qadd(song_dict, ctx.guild.id)
        await ctx.send(f"Added **{song_dict['title']}** to queue at position {queue_position}.", view=view)
        return

    # Set as current song and play immediately
    set_current_song(ctx.guild.id, song_dict)
    
    try:
        yt = youtube(url)
        audio = yt.streams.filter(only_audio=True).order_by('abr').last()
        
        path = os.path.join(os.getcwd(), "audio")
        out_file = audio.download(output_path=path)

        base, ext = os.path.splitext(out_file)
        new_file = base + '.flac'
        
        if os.path.isfile(new_file):
            await ctx.send("Using cached audio file...")
        else:
            os.rename(out_file, new_file)
        
        if not os.path.isfile(new_file):
            await ctx.send(f"Unable to download audio file")
            return

        await ctx.send(f"Now playing: **{song_dict['title']}** by {song_dict['artist']}")
        audio_source = discord.FFmpegPCMAudio(new_file)
        
        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            # Auto-play next song when current finishes - fix event loop issue
            def schedule_next():
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.create_task(play_next_song(ctx, vc))
                except RuntimeError:
                    # Event loop not available, skip auto-play
                    pass
            
            schedule_next()
        
        vc.play(audio_source, after=after_playing)
        
    except Exception as e:
        await ctx.send(f"Error playing song: Unable to play this track") 


@bot.slash_command(name="qtest", description="For testing the queue system")
async def qtest_button(ctx):
    # Create a test song for demonstration
    test_song = {
        'url': 'https://www.youtube.com/watch?v=XFkzRNyygfk',
        'title': 'Test Song',
        'artist': 'Test Artist',
        'thumbnail': 'https://cdns-images.dzcdn.net/images/cover/f08424290260e58c6d76275253b316fd/1900x1900-000000-80-0-0.jpg',
        'duration': '3:30',
        'video_id': 'XFkzRNyygfk'
    }
    view = Qadd(test_song, ctx.guild.id)
    await ctx.respond("A song is already playing.", view=view) 


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

@bot.slash_command(name="playlist", description="Play a YouTube playlist")
async def playlist(ctx: discord.ApplicationContext, url: str = Option(description="YouTube playlist URL")):
    await ctx.defer()  # This can take a while
    
    voice = ctx.author.voice
    if not voice:
        await ctx.respond("Please join a voice channel first!")
        return

    if not is_valid_youtube_playlist_url(url):
        await ctx.respond("Invalid YouTube playlist URL! Please make sure it's a valid playlist link.")
        return

    vc = connections.get(ctx.guild.id)
    if vc is None:
        try:
            vc = await voice.channel.connect()
            connections.update({ctx.guild.id: vc})
        except Exception as e:
            await ctx.respond("Unable to connect to voice channel. Please try again.")
            return

    # Extract playlist info
    playlist_info = extract_playlist_info(url)
    if not playlist_info:
        await ctx.respond("Failed to load playlist information. The playlist might be private or unavailable.")
        return

    if playlist_info['length'] == 0:
        await ctx.respond("This playlist appears to be empty.")
        return

    await ctx.respond(f"Loading playlist: **{playlist_info['title']}** by {playlist_info['owner']}\n"
                     f"Found {playlist_info['length']} videos. Adding to queue...")

    # Add all videos to queue
    added_count = 0
    failed_count = 0
    
    for i, video_url in enumerate(playlist_info['videos']):
        try:
            song_dict = create_song_dict(video_url)
            if song_dict and song_dict['title'] != "Unknown Title":
                queue_position = add_to_queue(ctx.guild.id, song_dict)
                added_count += 1
            else:
                failed_count += 1
            
            # Send progress updates for every 10 songs
            if (added_count + failed_count) % 10 == 0:
                await ctx.edit(content=f"Loading playlist: **{playlist_info['title']}**\n"
                              f"Processed {added_count + failed_count}/{playlist_info['length']} songs...")
        except Exception as e:
            failed_count += 1
            continue

    if added_count > 0:
        success_msg = f"Successfully added {added_count} songs from playlist **{playlist_info['title']}** to the queue!"
        if failed_count > 0:
            success_msg += f"\n{failed_count} songs were skipped (unavailable or private)."
        await ctx.edit(content=success_msg)
        
        # If nothing is currently playing, start playing the first song
        if not vc.is_playing() and not vc.is_paused():
            await play_next_song(ctx, vc)
    else:
        await ctx.edit(content="Unable to add any songs from this playlist. All videos may be unavailable or private.")


async def play_next_song(ctx, vc):
    try:
        guild_id = ctx.guild.id
        loop_mode = get_loop_mode(guild_id)
        current_song = get_current_song(guild_id)
        
        if loop_mode == "song" and current_song:
            next_song = current_song.copy()
        else:
            next_song = get_next_song(guild_id)
            
            if not next_song and loop_mode == "queue":
                history = get_or_create_history(guild_id)
                if len(history) > 1:
                    for song in reversed(history[1:]):
                        add_to_queue(guild_id, song)
                    next_song = get_next_song(guild_id)
        
        if not next_song:
            return

        if loop_mode == "song":
            song_start_times[guild_id] = time.time()
        else:
            set_current_song(guild_id, next_song)
        
        yt = youtube(next_song['url'])
        audio = yt.streams.filter(only_audio=True).order_by('abr').last()
        
        if not audio:
            await ctx.send(f"No audio stream available for **{next_song['title']}**. Skipping...")
            return await play_next_song(ctx, vc)
        
        path = os.path.join(os.getcwd(), "audio")
        out_file = audio.download(output_path=path)

        base, ext = os.path.splitext(out_file)
        new_file = base + '.flac'

        if not os.path.isfile(new_file):
            os.rename(out_file, new_file)

        audio_source = discord.FFmpegPCMAudio(new_file)
        
        def after_playing(error):
            if error:
                print(f'Player error: {error}')
            def schedule_next():
                try:
                    loop = asyncio.get_event_loop()
                    if loop and loop.is_running():
                        asyncio.create_task(play_next_song(ctx, vc))
                except RuntimeError:
                    pass
            
            schedule_next()
        
        vc.play(audio_source, after=after_playing)
        
        if loop_mode == "song":
            await ctx.send(f"Looping: **{next_song['title']}** by {next_song['artist']}")
        else:
            await ctx.send(f"Now playing: **{next_song['title']}** by {next_song['artist']}")
        
    except Exception as e:
        await ctx.send(f"Unable to play **{next_song.get('title', 'next song')}**. Skipping to next track...")
        await play_next_song(ctx, vc)


@bot.slash_command(name="queue", description="Show the current music queue")
async def show_queue(ctx: discord.ApplicationContext):
    queue = get_or_create_queue(ctx.guild.id)
    current_song = get_current_song(ctx.guild.id)
    
    embed = discord.Embed(title="Music Queue", color=discord.Colour.blue())
    
    if current_song:
        embed.add_field(
            name="🎵 Currently Playing",
            value=f"**{current_song['title']}** by {current_song['artist']}",
            inline=False
        )
    
    if queue:
        queue_text = ""
        max_length = 1000  # Leave some buffer below Discord's 1024 character limit
        songs_shown = 0
        
        for i, song in enumerate(queue):
            # Truncate title and artist if they're too long
            title = song['title'][:50] + "..." if len(song['title']) > 50 else song['title']
            artist = song['artist'][:30] + "..." if len(song['artist']) > 30 else song['artist']
            
            song_line = f"{i+1}. **{title}** by {artist}\n"
            
            # Check if adding this song would exceed the limit
            if len(queue_text) + len(song_line) > max_length:
                break
                
            queue_text += song_line
            songs_shown += 1
        
        # Add "more songs" indicator if we couldn't show all songs
        if songs_shown < len(queue):
            remaining = len(queue) - songs_shown
            more_text = f"... and {remaining} more song{'s' if remaining > 1 else ''}"
            # Make sure we have room for the "more" text
            if len(queue_text) + len(more_text) <= max_length:
                queue_text += more_text
            else:
                # If we can't fit the "more" text, remove the last song and add it
                lines = queue_text.strip().split('\n')
                if len(lines) > 1:
                    queue_text = '\n'.join(lines[:-1]) + '\n' + more_text
            
        embed.add_field(name="Up Next", value=queue_text if queue_text.strip() else "Queue is too large to display properly", inline=False)
        embed.set_footer(text=f"Total songs in queue: {len(queue)}")
    else:
        embed.add_field(name="Queue", value="Queue is empty", inline=False)
    
    await ctx.respond(embed=embed)


@bot.slash_command(name="help", description="Show bot commands and features")
async def help_command(ctx: discord.ApplicationContext):
    embed = discord.Embed(
        title="Music Bot Commands",
        description="Here are all the available commands:",
        color=discord.Colour.blurple()
    )
    
    embed.add_field(
        name="Playback Commands",
        value="`/play` - Search and play a song\n"
              "`/playurl` - Play from YouTube URL\n"
              "`/playlist` - Play entire YouTube playlist\n"
              "`/menu` - Show playback controls",
        inline=False
    )
    
    embed.add_field(
        name="Control Commands", 
        value="`/pause` - Pause playback\n"
              "`/resume` - Resume playback\n"
              "`/stop` - Stop and disconnect\n"
              "`/skip` - Skip current song\n"
              "`/loop` - Set loop mode (off/song/queue)",
        inline=False
    )
    
    embed.add_field(
        name="Queue & History Commands",
        value="`/queue` - Show current queue\n"
              "`/history` - Show recently played songs\n"
              "`/clearqueue` - Clear the queue\n"
              "`/clearhistory` - Clear song history",
        inline=False
    )
    
    embed.add_field(
        name="Utility Commands",
        value="`/joinvoice` - Join your voice channel\n"
              "`/validate` - Check if YouTube URL is valid",
        inline=False
    )
    
    embed.set_footer(text="💡 Use the menu command for an interactive player interface!")
    
    await ctx.respond(embed=embed)


@bot.slash_command(name="droptest", description="ts")
async def droptest(ctx):
    await ctx.respond("Dropdown test not implemented yet")

@bot.slash_command(name="skip", description="Skip the current song")
async def skip(ctx: discord.ApplicationContext):
    guild = ctx.guild
    vc = connections.get(guild.id)
    if vc is None:
        await ctx.respond("Bot is not connected to a voice channel.")
        return
    
    queue = get_or_create_queue(guild.id)
    if not queue and not vc.is_playing():
        await ctx.respond("Nothing to skip!")
        return
    
    if vc.is_playing() or vc.is_paused():
        vc.stop()  # Stop current song
        await ctx.respond("Skipped current song!")
        
        if queue:
            await play_next_song(ctx, vc)
    else:
        if queue:
            await play_next_song(ctx, vc)
            await ctx.respond("Started playing queue!")
        else:
            await ctx.respond("Nothing is currently playing!")


@bot.slash_command(name="history", description="Show recently played songs")
async def show_history(ctx: discord.ApplicationContext):
    history = get_or_create_history(ctx.guild.id)
    
    embed = discord.Embed(title="🕐 Song History", color=discord.Colour.purple())
    
    if history:
        history_text = ""
        for i, song in enumerate(history[:10]):
            history_text += f"{i+1}. **{song['title']}** by {song['artist']}\n"
        
        if len(history) > 10:
            history_text += f"... and {len(history) - 10} more songs"
            
        embed.add_field(name="Recently Played", value=history_text, inline=False)
        embed.set_footer(text=f"Total songs in history: {len(history)}")
    else:
        embed.add_field(name="History", value="No songs in history yet", inline=False)
    
    await ctx.respond(embed=embed)


@bot.slash_command(name="clearqueue", description="Clear the music queue")
async def clear_queue(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    queue = get_or_create_queue(guild_id)
    
    if not queue:
        await ctx.respond("Queue is already empty!")
        return
    
    cleared_count = len(queue)
    queue.clear()
    await ctx.respond(f"Cleared {cleared_count} song(s) from the queue!")


@bot.slash_command(name="clearhistory", description="Clear the song history")
async def clear_history(ctx: discord.ApplicationContext):
    guild_id = ctx.guild.id
    history = get_or_create_history(guild_id)
    
    if not history:
        await ctx.respond("History is already empty!")
        return
    
    cleared_count = len(history)
    history.clear()
    await ctx.respond(f"Cleared {cleared_count} song(s) from history!")


@bot.slash_command(name="validate", description="Validate a youtube URL")
async def validate_url(ctx, url: str = Option(description="YouTube URL to validate")):
    if is_valid_youtube_playlist_url(url):
        playlist_info = extract_playlist_info(url)
        if playlist_info:
            await ctx.respond(f"Valid YouTube playlist: **{playlist_info['title']}** by {playlist_info['owner']}\n"
                            f"Contains {playlist_info['length']} videos")
        else:
            await ctx.respond("Valid YouTube playlist URL, but couldn't extract details")
    elif is_valid_youtube_url(url):
        try:
            yt = youtube(url)
            await ctx.respond(f"Valid YouTube video: **{yt.title}** by {yt.author}")
        except:
            await ctx.respond("Valid YouTube video URL")
    else:
        await ctx.respond("Invalid YouTube URL or the video/playlist is unavailable.")


@bot.slash_command(name="loop", description="Control loop mode (off/song/queue)")
async def loop_command(ctx: discord.ApplicationContext, mode: str = Option(
    description="Loop mode", 
    choices=["off", "song", "queue"]
)):
    guild_id = ctx.guild.id
    
    if set_loop_mode(guild_id, mode):
        if mode == "off":
            await ctx.respond("Loop: Off")
        elif mode == "song":
            await ctx.respond("Loop: Current Song")
        elif mode == "queue":
            await ctx.respond("Loop: Queue")
    else:
        await ctx.respond("Invalid loop mode. Use: off, song, or queue")

bot.run(os.getenv('TOKEN'))
