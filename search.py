from youtube_search import YoutubeSearch

results = YoutubeSearch('everything in its right place', max_results=10).to_json()

print(results)
