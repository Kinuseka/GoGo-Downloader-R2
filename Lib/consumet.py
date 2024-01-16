from CFSession import cfSession

class ConsumetAPI:
    """Intended to scrape video sources from ConsumetAPI"""
    def __init__(self, base_url, video_id, source):
        self.base_url = base_url
        self.video_id = video_id
        self.source = source
        self.session = cfSession()
        
    def _get_api_data(self): 
        api = f"{self.base_url}/anime/gogoanime/watch/{self.video_id}?server={self.source}"
        return self.session.get(api).json()
        
    def get_m3u8_api(self) -> list:
        api = self._get_api_data()
        return api["sources"]
    
    def get_m3u8_files(self):
        """Return multiple links"""
        return self.get_m3u8_api()

    def get_referrer(self):
        return self._get_api_data()['headers']  