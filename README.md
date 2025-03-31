<h1 align="center">GoonTunes Music Bot</h1>
<p>This project is currently a work in progress, there will be bugs and missing features</p>

<h2>Usage</h2>

Installing GoonTunes
```bash
git clone https://github.com/Derukugis/Music-Bot.git
cd Music-Bot
pip install -r requirements.txt
python main.py
```
GoonTunes also requires [FFmpeg](https://github.com/BtbN/FFmpeg-Builds/releases) to be installed on your system.
<details>
<summary>Windows</summary>
<br>
https://github.com/BtbN/FFmpeg-Builds/releases
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

AUR package (Cross-platform)
```bash
yay -S ffmpeg
```

Arch liux
```bash
sudo pacman -S ffmpeg
```

Debian
```bash
sudo apt-get install ffmpeg
```

Ubuntu
```bash
sudo apt install ffmpeg
```


</details>

<h2>Commands</h2>

/menu - Bring up playback menu **[WIP]**
/play _Song Name_ - Play a song from youtube<br><br>
/playurl _URL_ - play a url from YouTube URL<br><br>
/pause - Pause the current playback<br><br>
/resume - Resume playback<br><br>
/joinvoice - Force the bot to join your current voice channel without playing anything.<br><br>
/stop - Cancel the current playback, bot will leave the voice channel.<br><br>
/validate - _URL_ check if a youtube URL is valid.
