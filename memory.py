from pytubefix import YouTube as youtube
import io


yt = youtube("https://www.youtube.com/watch?v=onRk0sjSgFU")

# Get the best audio stream
best_audio = yt.streams.filter(only_audio=True).order_by('abr').last()

# Create a bytes buffer to store the audio in memory
audio_buffer = io.BytesIO()

# Download the audio directly to memory
best_audio.stream_to_buffer(audio_buffer)

# Now the audio is stored in memory in audio_buffer
# You can access the bytes with audio_buffer.getvalue()
audio_data = audio_buffer.getvalue()

print(f"{yt.title} has been successfully loaded into memory.")
print(f"Audio size: {len(audio_data)} bytes")

audio = AudioSegment.from_file(io.BytesIO(audio_data))

ts = input("hey gng")
