from urllib.parse import urlparse, parse_qsl, urlunparse, urlencode
from collections.abc import Callable, Iterable, Mapping
from Varstorage import Configuration, Constants
from CFSession import cfSession, cfexception
from requests.exceptions import RequestException
from typing import Any
from pathlib import Path
import threading
import shutil
import m3u8
import pickle
import time
import os
import re
config = Configuration().load()

# bytes pretty-printing
UNITS_MAPPING = [
    (1<<50, ' PB'),
    (1<<40, ' TB'),
    (1<<30, ' GB'),
    (1<<20, ' MB'),
    (1<<10, ' KB'),
    (1, (' byte', ' bytes')),
]

def validatename(word_orig:str):
    """
    Copied from: https://github.com/Kinuseka/nScraper
    """
    word = word_orig
    forbidden = ['<', '>', ':', '"', "|", "?", "*"]
    for char in forbidden:
        word = word.replace(char, "")
    word = word.replace("\\","_")
    word = word.replace("/","_")
    return word

def pretty_size(bytes, units=UNITS_MAPPING):
    """Get human-readable file sizes.
    simplified version of https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)
    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

def UrlSearch(prepend):
    "Generate a valid search url based on given words"
    string = str(prepend)
    var = string.replace(" ", "%20")
    return f'{config.get_host}//search.html?keyword={var}'

def UrlFixer(url:str, flair: str):
    "Add flair to base url"
    return f'{url}{flair}'

def Get_ID(url):
    "Get video ID from episode link"
    url_parse = urlparse(url)
    return url_parse.path.split("/")[-1]

def append_query(url: str, key: str, value: str) -> str:
    url = url.rstrip('/')
    url_parsed = urlparse(url)
    query = dict(parse_qsl(url_parsed.query))
    query.update({key: value})
    new_url = url_parsed._replace(query=urlencode(query)).geturl()
    return new_url

def pagination_link(url, on, max, direction):
    if direction == "fwd" and on == max:
        return None
    elif direction == "prv" and on == 1:
        return None
    value = 1 if direction == "fwd" else -1
    final_value = sum((on,value))
    final = append_query(url, "page", final_value)
    return final

class RequestsClient():
    def download(self, uri, timeout=None, headers={}, verify_ssl=True):
        session = cfSession()
        o = session.get(uri, timeout=timeout, headers=headers)
        return o.text, o.url

class HlsObject():
    """
    An HlsObject is responsible for managing the m3u8 file and downloading the video file. To initiate the download process, use the .download() method
    """
    def __init__(self, 
                 m3u8_url: str, 
                 headers: dict,
                 file_name: str,
                 download_location: str,
                 extension = "mp4",
                 concurrency: int = 10,
                 daemon = True,
                ):
        self.url = m3u8_url
        self.headers = headers
        self.daemon = daemon
        self.download_location = download_location
        self.file_name = file_name
        #Set m3u8 instance
        self.playlist = m3u8.load(self.url, http_client=RequestsClient())
        self.duration = self.playlist.target_duration
        #Set directories
        self.cache_location = os.path.join(self.download_location, f".cache.{file_name}")
        self.final_location = os.path.join(self.download_location, f"{file_name}.{extension}")
        Path(self.download_location).mkdir(parents=True, exist_ok=True)
        Path(self.cache_location).mkdir(parents=True, exist_ok=True)
        self.semaphore = threading.Semaphore(concurrency)
        #Load pickle for possible resume
        self._pickled_directory = os.path.join(self.cache_location, "store.datadl")
        self._load_pickle()

        self.started_download = False
        #Threaded variables
        self.child_processes: list[Downloader_child] = []
        #Parent progress

    def _load_pickle(self) -> bool:
        "Loads existing progress"
        if os.path.isfile(self._pickled_directory):
            with open(self._pickled_directory, "rb") as f: 
                try:
                    self.map, self.progress = pickle.load(f)
                except (EOFError, pickle.UnpicklingError, MemoryError) as e:
                    print(e)
        else:
            self.map = []
            self.progress = {
                        "error": None,
                        "progress": 0,
                        "errored": 0,
                        "file_size": 0
                    }

    def _dump_pickle(self):
        "Dumps existing progress"
        with open(self._pickled_directory, "wb") as f:
            pickle.dump((self.map, self.progress), f)

    @property
    def segments(self):
        url = urlparse(self.url)
        path = url.path.split("/")[1:]
        if self._has_valid_url(self.playlist.segments.uri):
            return self.playlist.segments.uri
        else:
            return [f"{url.scheme}://{url.netloc}/{path[0]}/{path[1]}/{seg}"
           for seg in self.playlist.segments.uri]
        
    @property
    def segment_count(self):
        return len(self.segments)
    
    @property
    def is_download_done(self):
        return self.progress['progress'] == self.segment_count 
    
    def _has_valid_url(self, urls):
        pattern = r'^https?://[\w\-]+(\.[\w\-]+)+[/#?]?.*$'
        for url in urls:
            if re.match(pattern, url):
                return True
            else:
                return False

    def download(self):
        """Creates children, and runs them starting the download process"""
        if self.create_children():
            self.started_download = True
            self.start_children()

    def _create_child(self, segment_url, segment_id):
        """Creates a single children process"""
        thread = Downloader_child(url=segment_url, file_name=self.file_name, directory=self.cache_location, segment_id=segment_id, semaphore=self.semaphore, headers=self.headers, daemon=self.daemon)
        return thread
    
    def create_children(self):
        """Creates the children processes"""
        for num, segments in enumerate(self.segments):
            if num in self.map: continue
            child = self._create_child(segment_url=segments,segment_id=num)
            self.child_processes.append(child)
        else:
            return True

    def start_children(self):
        """Starts the generated children"""
        for child in self.child_processes:
            child.start()

    def download_progress(self):
        "Blocks main_thread and shows the download progress during the process. Useful for debugging"
        if not self.started_download:
            print("Download has not started")
            return
        while True:
            self.update_progress()
            if self.is_download_done:
                break
            print(f"Downloaded: {self.progress['progress']}/{self.segment_count}/-{self.progress['errored']} Size: {self.progress['file_size']}", end="\r")
            time.sleep(1)

    def update_progress(self):
        """Invoke this to update status updates on children processes"""
        done = []
        errored = []
        file_size = 0
        for children in self.child_processes:
            file_size += children.progress["file_size"]
            if children.progress["done"] and not children.progress["error"]:
                done.append(1)
                if children.segment_id in self.map:
                    self.map.append(children.segment_id)
            elif children.progress["error"]:
                errored.append(1)
        self.progress['file_size'] = file_size
        self.progress['progress'] = len(done)
        self.progress['errored'] = len(errored)

    def arrange_files(self):
        """Arrange the downloaded files"""
        if not self.is_download_done:
            return False
        with open(self.final_location, "wb") as f:
            for child in self.child_processes:
                with child.file_open() as file:
                    #Do chunked read to save memory
                    for chunk in iter(lambda: file.read(4096), b""):
                        f.write(chunk)
                child.delete_file()
                
    def cache_clear(self):
        """Clean temporary files/folder on cache for this particular instance. Once you call this, the parent process is now broken and must be discarded."""
        cache_dir = self.cache_location
        if not os.path.exists(cache_dir): return
        for filename in os.listdir(cache_dir):
            # Create absolute path
            filepath = os.path.join(cache_dir, filename)
            try:
                # If it is a file or symlink, remove it
                if os.path.isfile(filepath) or os.path.islink(filepath):
                    os.unlink(filepath)
                # If it is a directory, remove it
                elif os.path.isdir(filepath):
                    shutil.rmtree(filepath)
            except Exception as e:
                print('[CacheClean] Failed to delete %s. Reason: %s' % (filepath, e))
        os.rmdir(cache_dir)
                
    def close(self):
        """Gracefully close downloader and save progress"""
        #post store
        self.update_progress()
        #self._dump_pickle()
        
                    
class Downloader_child(threading.Thread):
    def __init__(self, url, file_name, directory, segment_id, headers, semaphore: threading.Semaphore, finished_state = False, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.headers = headers
        self.directory = directory
        self.filename = file_name
        self.segment_id = segment_id
        self.final_name = f"{file_name}.{segment_id}"
        self.semaphore = semaphore
        self.progress = {
            "file_name": file_name,
            "error": None,
            "done": False,
            "file_size": 0
        }
        self.session = cfSession()
        self.session.session.headers = headers
        Path(self.directory).mkdir(parents=True, exist_ok=True)

    def file_open(self):
        """Return a Readable stream"""
        return open(os.path.join(self.directory, self.final_name), "rb")
    
    def delete_file(self):
        """Destroy contents, once you call this the child process is now broken and must be discarded"""
        os.remove(os.path.join(self.directory, self.final_name))

    def run(self):
        self.semaphore.acquire() 
        last_exception = None
        for i in range(5):
            recorded_chunks = 0
            with open(os.path.join(self.directory, self.final_name), "wb") as f:
                try:
                    response_stream = self.session.get(self.url, stream=True, timeout=120)
                    for chunks in response_stream.iter_content(chunk_size=4096):
                        f.write(chunks)
                        recorded_chunks += len(chunks)
                        self.progress["file_size"] = recorded_chunks
                    else:
                        self.progress["done"] = True
                        self.semaphore.release()
                        break
                except (cfexception.CFException, RequestException) as e:
                    print(f"thr: {self.segment_id} Attempt {i+1}/5: Error: {e}")
                    self.progress["file_size"] -= recorded_chunks
                    last_exception = e
        else:
            self.progress["done"] = True
            self.progress["error"] = last_exception

if __name__ == "__main__":
    hls = HlsObject("https://www041.vipanicdn.net/streamhls/04d139ee5086804474adaefc664a7927/ep.4.1697767391.480.m3u8", file_name='temporary_name.mp4',headers={"Referer":"https://goone.pro/streaming.php?id=MzgzMTc=&title=Steins%3BGate+Episode+1"})
    # print(hls.segments)
    hls.download()
    hls.download_progress()
    hls.arrange_files() 