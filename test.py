from youtube_search import YoutubeSearch
import asyncio

search_term = "creep"

async def search():
    try:
        results = await asyncio.to_thread(
            lambda: YoutubeSearch(search_term, max_results=6).to_dict()
        )
        if not results:
            return []
        
        for result in results:
            if result["title"].casefold().count(result["channel"].casefold()) == 1:
                result["title"] = result["title"].casefold().replace(result["channel"].casefold(), '')
                result["title"] = result["title"].replace(" - ".casefold(), '')
            print(result["channel"], "-", result["title"])
        return result["title"], result["id"]  # Returning the search results
    
    except Exception as e:
        print(f"Error during YouTube search: {e}")
        return []

# Properly execute the async function
asyncio.run(search())
