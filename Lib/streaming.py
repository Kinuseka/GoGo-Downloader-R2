"""
GoGoDownloader.Lib.streaming
----------------------------
Not fully implemented, this will be used in the future
if we find a way to scrape video source
"""

from CFSession import cfSession
from bs4 import BeautifulSoup

class GogoStream:
    def __init__(self, url):
        self.url = url
        self.session = cfSession()
        response = self.session.get(self.url)
        self.parsed = BeautifulSoup(response.content, "html.parser")

    def get_streaming_url(self):
        container_anime = self.parsed.find("div", class_="anime_muti_link")
        vidcdn_url = container_anime.find("a", class_="active")["data-video"]
        return vidcdn_url
    

    
