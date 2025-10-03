<h1 align="center">GoonTunes</h1>
<p>Goontunes is a discord music bot with support for youtube playback.</p>

<h2>Commands</h2>


**/play** _Song Name_ - Search and play a song from YouTube with autocomplete<br>
**/playurl** _URL_ - Play a song directly from a YouTube URL<br>
**/playlist** _URL_ - Load and play an entire YouTube playlist<br>
**/menu** - Display interactive playback controls with real-time progress<br>
**/pause** - Pause the current playback<br>
**/resume** - Resume paused playback<br>
**/stop** - Stop playback and disconnect from voice channel<br>
**/skip** - Skip to the next song in queue<br>
**/loop** _mode_ - Set loop mode: `off`, `song`, or `queue`<br>
**/queue** - Display the current music queue<br>
**/clearqueue** - Clear all songs from the queue<br>
**/history** - Show recently played songs<br>
**/clearhistory** - Clear the song history<br>
**/joinvoice** - Join your current voice channel<br>
**/validate** _URL_ - Check if a YouTube URL or playlist is valid<br>
**/help** - Show all available commands and features<br>



<h2>Installing and running GoonTunes</h2>

```bash
git clone https://github.com/Derukugis/Music-Bot.git
cd Music-Bot
pip install -r requirements.txt
# Create a .env file with your Discord bot token
echo "TOKEN=your_discord_bot_token_here" > .env
python main.py
```
<h3>FFmpeg Installation</h3>

<details>
<summary>Windows</summary>
<br>

1. Download FFmpeg from [here](https://github.com/BtbN/FFmpeg-Builds/releases)<br>
2. Extract the archive<br>
3. Add the `bin` folder to your system PATH<br>
</details>

<details>
<summary>MacOS</summary>
<br>
  
```bash
brew install ffmpeg
```
</details>

<details>
<summary>Linux</summary>
<br>

**Arch Linux (AUR)**
```bash
yay -S ffmpeg
```

**Arch Linux (pacman)**
```bash
sudo pacman -S ffmpeg
```

**Debian/Ubuntu**
```bash
sudo apt update
sudo apt install ffmpeg
```
</details>

<h2>Dependencies</h2>

Install all dependencies with:
```bash
pip install -r requirements.txt
```

