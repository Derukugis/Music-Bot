from youtube_search import YoutubeSearch

results = YoutubeSearch('creep', max_results=10).to_json()

print(results)
