from processor import UrlFixer, UrlSearch, pagination_link, Get_ID, pretty_size, validatename, HlsObject
from Lib import Goscraper, Prettify, EpisodeScraper, ConsumetAPI
from Varstorage import Configuration, Constants
from pathlib import Path
import time, os
from terminology import in_green

config = Configuration().load()
config.self_check()

def user_input(text, valid: list, msg="Enter valid variables"):
    "Get a list of valid integers, add any on list to allow any input other than blank or whitespace"
    user = None
    while True:
        user = input(text).strip()
        try:
            user = int(user)
        except ValueError:
            if "int" in valid:
                print(msg)
                continue
        if user and "any" in valid:
            return user
        if user in valid:
            return user
        if isinstance(user, int) and "int" in valid:
            return user
        print(msg)

def Episode_UI(url, anime_title):
    "Collect episodes and UI for bulk download"
    goepisode = EpisodeScraper(url)
    available_episodes = goepisode.get_episodes()
    preprint = Prettify()
    preprint.define_alignment(tabs=1)
    preprint.add_tab()
    preprint.add_line(f"Found {available_episodes} episodes!")
    preprint.add_tab("Bulk downloader")
    preprint()
    starting_ep = user_input(text="Start from episode:", valid=[i+1 for i in range(available_episodes)], msg="Enter valid number")
    ending_ep = user_input(text="End at episode:", valid=[i+1 for i in range(available_episodes)], msg="Enter valid number")
    for i in range(starting_ep, ending_ep+1):
        preprint = Prettify()
        preprint.define_alignment(tabs=1)
        preprint.add_tab()
        preprint.add_line(f"Downloading Episode {i} / {ending_ep}")
        preprint.add_tab()
        preprint()
        episode_link = goepisode.get_episode_link(i)
        exit_code = Download_UI(episode_link, anime_title=anime_title, episode_number=i)
        if exit_code == 2:
            return exit_code

def Download_UI(url, anime_title, episode_number):
    "Get download links and show download UI"
    Path(Constants.download_folder).mkdir(parents=True, exist_ok=True) #Create Downloads folder
    #===
    preprint = Prettify()
    preprint.define_alignment(tabs=1)
    preprint.add_tab()
    preprint.add_line("Getting m3u8 file...")
    preprint.add_tab(char="-")
    preprint()
    video_id = Get_ID(url)
    consumet = ConsumetAPI(base_url=config.get_consumet_api, video_id=video_id,source="vidstreaming")
    video = consumet.get_m3u8_file(config.video_quality_preference, force=(config.video_quality_mode == "manual"))
    print(f"Preferred Quality: {config.video_quality_preference}")
    print(f"Quality Selected: {video['quality']}")
    headers = consumet.get_referrer()
    if not video:
        print("We are not able to find streamable media for this title")
        return 1
    #Download the file
    file_name = validatename(f"{anime_title}_{episode_number}")
    hls = HlsObject(m3u8_url=video['url'], headers=headers,file_name=file_name, download_location=os.path.join(Constants.download_folder, validatename(anime_title)))
    hls.download() #Initiate download
    print(f"Downloading: {anime_title}")
    error_msg = ""
    try:
        while True:
            hls.update_progress()
            segment_done = hls.progress['progress']
            segment_available = hls.segment_count
            segment_errored = hls.progress['errored']
            data_downloaded = hls.progress['file_size']
            try:
                percent_done = round(segment_done / segment_available * 100, 2)
            except ZeroDivisionError:
                percent_done = 0
            if segment_errored:
                error_msg = f"/Err:{segment_errored}"
            print(in_green(f"=== Progress: [{segment_done}/{segment_available}]{error_msg} ** {percent_done}% - {pretty_size(data_downloaded)} ==="), end="\r")
            if segment_done == segment_available:
                print("\n Download successful!")
                hls.arrange_files()
                hls.cache_clear()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        hls.close()
        return 2

def Genre_UI():
    "Show available genres on site"
    gogo_page = Goscraper(config.get_host)
    genre_list = gogo_page.get_genres()
    preprint = Prettify()
    preprint.define_alignment(tabs=1)
    preprint.add_tab(data="Found Genres", lines=33)
    valid = []
    for num, genre_each in enumerate(genre_list):
        preprint.add_sort(key=num+1, value=genre_each['genre-name'], separator=".")
        valid.append(num+1)
    preprint.add_tab(char='-',lines=33)
    preprint()
    selection = user_input("Select:", valid=valid)
    new_url = UrlFixer(config.get_host, genre_list[selection-1]['flair'])
    print("\tLoading (restart if it took >10s)")
    return Home_UI(host=new_url)

def Home_UI(host):
    'Display main results'
    gogo_page = Goscraper(host)
    if not gogo_page.get_result_count():
        print("\tThere are no results found")
        return 1
    result_title = gogo_page.get_titles()
    pagination = gogo_page.get_pagination()
    preprint = Prettify()
    preprint.define_alignment(tabs=1)
    preprint.add_tab("Results",lines=33)
    valid = []
    for num, res_tile in enumerate(result_title):
        preprint.add_sort(key=num+1, value=res_tile["title_name"], separator=".)")
        if res_tile.get('episode'):
            preprint.add_line(f"\t Episode: {res_tile['episode']}")
        preprint.add_tab(char="-",lines=33)
        valid.append(num+1)
    [valid.append(each) for each in Constants.pagination_commands]
    preprint.add_line(f"There are {gogo_page.get_result_count()} results found")
    if pagination['page_total'] > 1:
        preprint.add_line("To switch a page: << or >>")
        preprint.add_line(f"Page: {pagination['page_on']}/{pagination['page_total']}")
    preprint()
    while True: #use loops to prevent halting of application for when pagination returns None
        selection = user_input("Select:", valid=valid)
        if selection in Constants.pagination_commands:
            if selection == Constants.pagination_commands[0] or selection == Constants.pagination_commands[3]:
                #Forwards
                result = pagination_link(host, pagination['page_on'], pagination['page_total'], 'fwd')
            elif selection == Constants.pagination_commands[1] or selection == Constants.pagination_commands[2]:
                #Backwards
                result = pagination_link(host, pagination['page_on'], pagination['page_total'], 'prv')
            if result:
                return Home_UI(result)
        else:
            new_url = UrlFixer(config.get_host, result_title[selection-1]['flair']) #Use base url for this
            if res_tile.get('episode'):
                return Download_UI(new_url, result_title[selection-1]['title_name'], result_title[selection-1]['episode'])#This needs to go straight to Downloader or Video Scraper
            return Episode_UI(new_url, result_title[selection-1]['title_name'])
            #Next step is get download link and or skip to episode download

def ResultZone(mode, value=None):
    if mode == "Home":
        return Home_UI(config.get_host)        
    elif mode == "Genre":
        Genre_UI()
    elif mode == "Search":
        return Home_UI(UrlSearch(value)) 

def main():
    preprint = Prettify()
    preprint.define_alignment(tabs=1)
    preprint.add_tab(lines=33)
    preprint.add_line("\tGoGoDownloader R2")
    preprint.add_tab(lines=33)
    preprint.add_sort(key="1",value="Search at Homepage", separator=".)")
    preprint.add_sort(key="2",value="Search by Genres", separator=".)")
    preprint.add_line("Or type in the title, to search")
    preprint.add_tab(lines=33)
    preprint()
    selection = user_input("\tEnter Number/Search title:", [1,2,"any"])
    print("\tLoading (restart if it took >10s)")
    if selection == 1:
        return ResultZone("Home")
    elif selection == 2:
        return ResultZone("Genre")
    else:
        return ResultZone("Search", value=selection)
if __name__ == "__main__":
    main()