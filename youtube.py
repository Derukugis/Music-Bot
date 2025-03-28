from pytubefix import YouTube as youtube
import os
id = "onRk0sjSgFU"
yt = youtube(f"https://youtube.com/watch/{id}")

audio = yt.streams.filter(only_audio=True).order_by('abr').last()

path = os.path.join(os.getcwd(), "audio")

out_file = audio.download(output_path=path)

# save the file
base, ext = os.path.splitext(out_file)
new_file = base + '.mp3'
os.rename(out_file, new_file)

print(yt.title + " has been successfully downloaded.")