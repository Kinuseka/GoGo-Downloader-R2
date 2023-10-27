from CFSession import cfSession
from CFSession import cfexception
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import itertools

class EpisodeScraper:
    """Scrape for available episodes"""
    def __init__(self, url: str):
        self.url = url
        session = cfSession()
        response = session.get(url)
        try:
            response.raise_for_status()
        except cfexception.HTTPError as e:
            code = e.response.status_code
            raise AttributeError(f"[Scraping Error] Error scraping, site returned http code: {code}") #Placeholder error, might use custom one, but for now use Attribute error for scraping issues
        self.parser = BeautifulSoup(response.content, 'html.parser')
    
    def _parse_url(self):
        return urlparse(self.url)

    def get_episodes(self):
        "Returns maximum episodes"
        return int(self.parser.find('a',class_='active')['ep_end'])
    
    def get_episode_link(self, value):
        "Returns a link of a specific episode, returns None if invalid"
        max_ep = self.get_episodes()
        if value > max_ep:
            return None
        url_parsed = self._parse_url()
        episode_id = self.get_episode_id(value)
        return f"{url_parsed.scheme}://{url_parsed.netloc}/{episode_id}"
    
    def get_episode_id(self, value):
        url_parsed = self._parse_url()
        title_flair = url_parsed.path.split("/")[-1]
        return f"{title_flair}-episode-{value}"
    
    def get_id(self):
        url_parsed = self._parse_url()
        return url_parsed.path.split("/")[-1]
    

#Notice: The exceptions with Attribute errors are only placeholders
class Goscraper:
    """GoGo Anime API"""
    def __init__(self, url: str):
        self.url = url
        self.session = cfSession()
        #Scrape Data from WEB
        response = self.session.get(url)
        try:
            response.raise_for_status()
        except cfexception.HTTPError as e:
            code = e.response.status_code
            raise AttributeError(f"[Scraping Error] Error scraping, site returned http code: {code}") #Placeholder error, might use custom one, but for now use Attribute error for scraping issues
        self.parsed = BeautifulSoup(response.content, 'html.parser')

    def _get_titles_raw(self, associated_episodes = False, associated_flair = False):
        """
        Scrapes website and returns a ResultSet object
        associated_episodes: Returns an episode number if the title is a direct episode link, usually this is true for home page. Returns None if nothing is found
        associated_flair: Returns a list of flairs of the specific title, usually from the same index, Flairs can be processed into URLS. Returns None if nothing is found
        """
        if associated_episodes and associated_flair: raise AttributeError("[Exclusivity Error] Only one kwargs can be True") 
        if associated_episodes:
            return self.parsed.find_all('p', class_='episode')
        elif associated_flair:
            titles = self.parsed.find_all('p',class_='name')
            flairs = []
            for flair in titles:
                pre_proc = flair.find('a')['href']
                flairs.append(pre_proc)
            return flairs
        else:
            return self.parsed.find_all('p',class_='name')

    def _get_genres_raw(self, associated_flair = False):
        """
        Scrapes website for available genres. Returns ResultSet
        By default returns only the name of each genre 
        associated_flair: Returns a list of flairs of the specific genre, they are usually in the same index. Flairs can be processed into URLS. Returns None if nothing is found
        """
        top_genre = self.parsed.find('li', class_='movie genre hide')
        genre_container = top_genre.find('ul')
        genre_all = genre_container.find_all('a')
        genre_data = []
        for genre in genre_all:
            if associated_flair:
                genre_data.append(genre['href'])
            else:
                genre_data.append(genre)
        return(genre_data)
    
    def get_titles(self):
        """Returns a user friendly data of the available titles and flairs."""
        titles = self._get_titles_raw()
        episodes = self._get_titles_raw(associated_episodes=True)
        flairs = self._get_titles_raw(associated_flair=True)
        scrape_res = []
        for (title, episode, flair) in itertools.zip_longest(titles, episodes, flairs) :
            scrape_data = {
                "title_name": None,
                "episode": None,
                "flair": None
            }
            scrape_data["title_name"] = title.text.strip()
            if episode:
                scrape_data["episode"] = int(episode.text.replace("Episode ", "").strip())
            scrape_data["flair"] = flair
            scrape_res.append(scrape_data)
        return scrape_res

    def get_result_count(self):
        "Returns the number of results"
        return len(self.get_titles())
    
    def get_pagination(self):
        """Gets the pagination of the webpage and returns the current page and the total pages available"""
        pagination_scraped = self.parsed.find('ul',class_='pagination-list')
        if not pagination_scraped: # If we cannot find a pagination-list then assume a one page
            return {
                'page_on': 1,
                'page_total': 1
            }
        current_page = int(pagination_scraped.find('li', class_ ="selected").text.strip())
        total_page = len(pagination_scraped.find_all('a'))
        pagination_data = {
            'page_on': current_page,
            'page_total': total_page
        }
        return pagination_data
    
    def get_genres(self):
        "Returns a user friendly data of the available genres and flairs."
        genre_names = self._get_genres_raw()
        genre_flairs = self._get_genres_raw(associated_flair=True)
        genre_processed_data = []
        for (name, flair) in itertools.zip_longest(genre_names, genre_flairs):
            genre_scraped = {
                "genre-name": None,
                "flair": None
            }
            genre_scraped["genre-name"] = name.text.strip()
            genre_scraped["flair"] = flair
            genre_processed_data.append(genre_scraped)
        return genre_processed_data
    
if __name__ == "__main__":
    gogo = Goscraper('https://gogoanime.vc')
    print(gogo.get_titles())
    print(gogo.get_result_count())
    print(gogo.get_pagination())
    print(gogo.get_genres())


