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
    
    def get_m3u8_file(self, quality="1080p", **kwargs):
        """Get one single source based on quality"""
        suggested_quality = self.pick_quality(quality, **kwargs)
        return suggested_quality
    
    def pick_quality(self, preferred_quality, force = False):
        qualities = self.get_m3u8_files()
        if force:
            for quality in qualities:
                if quality["quality"] == preferred_quality:
                    return quality
            else:
                return None
        quality_heiarchy = ["1080p", "720p", "480p", "360p", "default","backup"]
        qualities.reverse()
        #get backup for last
        qualities = [ quality for quality in qualities if quality["quality"] not in ['backup','default']]
        if preferred_quality == "best":
            return qualities[0]
        for quality in qualities:
            if quality["quality"] == preferred_quality:
                return quality
        #Second attempt with automatic
        for quality in qualities:
            for qualh in quality_heiarchy:
                if quality["quality"] ==  qualh:
                # preferred_quality = quality_heiarchy[index+1]
                    return quality
        else:
            return None

    def get_referrer(self):
        return self._get_api_data()['headers']  