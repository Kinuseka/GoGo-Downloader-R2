import yaml
import os

class Constants:
    pagination_commands = [">>", "<<", "prv", "frw"]
    download_folder = os.path.join(os.getcwd(), "Downloads")
    config_default = {
            "Video": {
                "quality": 'best',
                "selection": 'auto',
                "source": 'built-in'
            },
            "Network": {
                "base": "https://gogoanime3",
                "domain": "net",
                "consumet": None,
                "consumet_video_server": 'vidstreaming'
            }
        }

class Configuration:
    def __init__(self, name="config.yml"):
        self.name = name
        #Data template sets the default recommended configuration
        self.data_template = Constants.config_default
        self.valid_video_quality = ["1080p","720p","480p","360p","best"]
        self.valid_video_mode = ["auto","manual"]
        self.valid_video_source = ['built-in', 'consumet']
        self.valid_consumet_video_server = ['vidstreaming', 'gogocdn', 'streamsb']
    def load(self):
        "Load, returns itself"
        with open(self.name, "r") as f:
            self.data = yaml.safe_load(f)
        return self
    def self_check(self):
        if self.video_quality_preference not in self.valid_video_quality:
            raise ValueError(f"{self.video_quality_preference} is not a valid option")
        if self.video_quality_mode not in self.valid_video_mode:
            raise ValueError(f"{self.video_quality_mode} is not a valid option")
        if self.video_source not in self.valid_video_source:
            raise ValueError(f"{self.video_source} is not a valid option")
        if self.video_source == self.valid_video_source[1]:
            if not self.get_consumet_api:
                raise ValueError(f"{self.valid_video_source[1]} is used but the required value is {self.get_consumet_api}")
            if self.get_consumet_video_server not in self.valid_consumet_video_server:
                raise ValueError(f"{self.get_consumet_video_server} is not a valid option")
            

    def generate_config(self):
        with open(self.name, "w") as f:
            yaml.dump(self.data_template, f)
    @property
    def get_host(self):
        domain = self.data["Network"]["domain"] 
        return f"{self.get_base}.{domain}"
    @property
    def get_base(self):
        domain = self.data["Network"]["base"]
        return domain
    @property
    def get_consumet_api(self):
        api = self.data["Network"]["consumet"]
        return api
    @property
    def get_consumet_video_server(self):
        vidserver = self.data["Network"]["consumet_video_server"]
        return vidserver
    @property
    def video_quality_search(self):
        return self.data["Video"]["enable"]
    @property
    def video_quality_preference(self):
        value = self.data["Video"]["quality"]
        return value
    @property
    def video_quality_mode(self):
        return self.data["Video"]["selection"]
    @property
    def video_source(self):
        return self.data['Video']['source']

if __name__ == "__main__":
    config = Configuration()
    config.generate_config()
    config.load()
    print(config.get_host)