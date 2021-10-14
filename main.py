#!/usr/bin/python3

from sys import exit, argv as sys_argv, executable as sys_executable
from subprocess import check_call, CalledProcessError
from shutil import which
from urllib.parse import urlparse, urlunparse
import re
import os
import concurrent.futures

###########

if __name__ == "__main__":
    try:
        import youtube_dl
        import yaml
        from prettytable import PrettyTable
        from bs4 import BeautifulSoup
    except ModuleNotFoundError as e:
        print("Some required modules were not found:\n", e, "\n\nPlease ensure all modules listed in requirements.txt are installed.")
        exit()
else:
    import youtube_dl
    from bs4 import BeautifulSoup

###########

class Logger(object):
    def __init__(self, verbosity):
        self.verbosity = verbosity
        self.output = ""

    def debug(self, msg):
        self.output += msg
        if self.verbosity > 2:
            print(msg)

    def warning(self, msg):
        if self.verbosity > 1:
            print(msg)

    def error(self, msg):
        if self.verbosity > 0:
            print(msg)

class Anime():
    def __init__(self):
        self.downloader = youtube_dl.YoutubeDL()
        # Create reference to config
        self.ytdl_config = self.downloader.params

        # Information extractors
        ## ie._downloader.params are a reference to self.downloader.params
        self.playlist_ie = youtube_dl.extractor.crunchyroll.CrunchyrollShowPlaylistIE(self.downloader)
        self.ie = youtube_dl.extractor.crunchyroll.CrunchyrollIE(self.downloader) 

        # Default ytdl config
        self.ytdl_config.update({
            "postprocessors": [{"key": "FFmpegEmbedSubtitle"}],
            "ignoreerrors": True,
            "nooverwrites": True,
            "allsubtitles": True,
            "writesubtitles": True,
            "continuedl": True,
            })

        # Default config
        self.config = {
            "title": None,
            "id": None,
            "videos": None,
            "url": None,
            "username": None,
            "password": None,
            "output": None,
            "verbosity": 0,
            "ffmpeg_location": None, # Will check in path
            "custom": {},
            "downloaded": [],
        }
        
        # Behaviour
        self.check_all = False
        self.max_threads = 50
        self.max_dl_threads = 10

        # Current download threads
        self.dl_threads = []

    def video_info(self, index, url):
        try:
            return (index, self.ie._real_extract(url))
        except (youtube_dl.utils.DownloadError, youtube_dl.utils.ExtractorError) as error:
            return (index, {"error": str(error)})

    def update_config(self):
        """
        Update the downloader and information extractor config with the values set in this instance.
        """

        # Update config with new values
        self.ytdl_config.update({
        "quiet": False if self.config["verbosity"] > 4 else True,
        "username": self.config["username"],
        "password": self.config["password"],
        "logger": Logger(self.config["verbosity"]),
        "verbose": True if self.config["verbosity"] > 3 else False,
        "ffmpeg_location": self.config["ffmpeg_location"],
        "outtmpl": self.config["output"],
        })

        # Update config with custom values
        self.ytdl_config.update(self.config["custom"])

    def print_info(self):
        if not self.config["videos"]:
            self.get_info()

        table = PrettyTable(["Index", "Season", "Episode", "Language"])

        skip_part = False
        for index, video_dict in sorted(self.config["videos"].items(), key=lambda x: int(x[0])):
            if "/episode-1-" in video_dict["url"]:
                skip_part = True if "error" in video_dict else False
                if not skip_part:
                    table.add_row([index, video_dict["season_number"], video_dict["episode_number"], video_dict["formats"][0]["language"]])
            elif not skip_part:
                if not "error" in video_dict:
                    table.add_row([index, video_dict["season_number"], video_dict["episode_number"], video_dict["formats"][0]["language"]])

        print(table)


    def get_info(self):
        """
        Creates self.config["title"], self.config["id"] and self.config["videos"]
        self.config["videos"][index]: "_type", "url", "ie_key", "id", "title", "description", "duration", "thumbnail", "uploader", "series", "season", "episode", "episode_number", "subtitles", "formats", "season_number", "timestamp"
        """

        self.update_config()
        playlist_info = {}

        # Get basic playlist info
        if not self.config.get("html_path"):
            try:
                playlist_ie_return = self.playlist_ie._real_extract(self.config["url"])["entries"]
                playlist_info.update({
                    "title": playlist_ie_return["title"],
                    "id": playlist_ie_return["id"],
                    "urls": [entry["url"] for entry in playlist_ie_return]
                    })
            # Workaround - HTTP Error 403
            except youtube_dl.utils.ExtractorError:
                
                print(f"Could not access {self.config['url']}. Please download the page manually.")
                self.config["html_path"] = get_path(["cr.html", "cr.htm"], use_filedialog, msg="Please enter the path of the html file > ")
                playlist_info.update({
                    "urls": flattened_list(load_urls_from_html(self.config["html_path"]))
                    })
        else:
            playlist_info.update({"urls": flattened_list(load_urls_from_html(self.config["html_path"]))})

        # Check which parts of the playlist are available to the user (to reduce requests)
        # The playlist_info["urls"] list are is sorted by language and season
        # Each season / sequence of episodes in one language begins with "/episode-1-" in its URL
        if not self.check_all:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                threads = []
                for index, url in enumerate(playlist_info["urls"]):
                    if "/episode-1-" in url:
                        thread = executor.submit(self.video_info, index, url)
                        threads.append(thread)
                playlist_info["entries"] = {}
                for thread in concurrent.futures.as_completed(threads):
                    result = thread.result()
                    # result[0] contains the index to the corresponding element in playlist_info["urls"],
                    # result[1] the data from self.video_info()
                    playlist_info["entries"].update({
                        result[0]: result[1]
                        })
                    playlist_info["entries"][result[0]].update({
                        "url": playlist_info["urls"][result[0]]
                        })

        # Get detailed infos about the videos
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            threads = []
            skip_part = False
            for index, url in enumerate(playlist_info["urls"]):
                # Skip because the info about the fist episodes of each video
                # sequence was already gathered (if self.check_all is False)
                if not self.check_all and "/episode-1-" in url:
                    # If there has been an error, skip the rest of the sequence
                    skip_part = True if "error" in playlist_info["entries"].get(index) else False
                elif not skip_part:
                    thread = executor.submit(self.video_info, index, url)
                    threads.append(thread)
            for thread in concurrent.futures.as_completed(threads):
                result = thread.result()
                # result[0] contains the index to the corresponding element in playlist_info["urls"],
                # result[1] the data from self.video_info()
                playlist_info["entries"].update({
                    result[0]: result[1]
                    })
                playlist_info["entries"][result[0]].update({
                    "url": playlist_info["urls"][result[0]],
                    "playlist_index": result[0]
                    })
                if not "error" in result[1]:
                    del playlist_info["entries"][result[0]]["formats"][1:]

        # Save to config
        self.config.update({"videos": playlist_info["entries"]})

        # Set tile and an unique id if not already set
        if not (self.config["title"] and self.config["id"]):
            for index, video in playlist_info["entries"].items():
                if "series" in video.keys() and "id" in video.keys():
                    self.config.update({
                        "title": playlist_info["entries"][index]["series"],
                        "id": playlist_info["entries"][index]["id"]
                    })
                    break

    def start_download(self, dl_index):
        self.update_config()

        dl_videos = [self.config["videos"][index] for index in dl_index]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_dl_threads) as executor:
            for video_dict in dl_videos:
                thread = executor.submit(self._download, video_dict)
                self.dl_threads.append(thread)

    def _download(self, video_dict):
        ytdl_config = self.ytdl_config.copy()
        ytdl_config["outtmpl"] = ytdl_config["outtmpl"].replace("%(playlist_index)s", str(video_dict['playlist_index']))

        # Create a new downloader object with copy of current config and self._hook as hook
        downloader = youtube_dl.YoutubeDL(ytdl_config)
        downloader.params.update({"progress_hooks": [self._hook]})

        downloader.download([video_dict["url"]])

    def _hook(self, downloader):
        if downloader["status"] == "finished":
            print(f"Finished downloading ", os.path.basename(downloader["filename"]))

###########

def save_config():
    global config, w_anime

    # Update global config from Anime instace
    config["anime"].update({w_anime.config["title"]: w_anime.config})

    # Write to config file
    with open(config_path, "w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)

def remove_lang_tag(url):
    url_components = list(urlparse(url))
    url_components[2] = path=re.sub(r"^\/[a-z]{2}\/", "", url_components[2])
    return urlunparse(url_components)

def load_urls_from_html(html_path):
    """
    Takes the path of a crunchyroll page's html file.
    Returns a list of lists, each containing the links to all videos of one video sequence
    (season and language), each sorted in ascending order.
    """
    res = []
    with open(html_path, "r", encoding="utf-8") as html_file:
        soup = BeautifulSoup(html_file, features="html.parser")
    
    # Extract URLs
    episode_sequences = soup.find_all("li", class_="season small-margin-bottom")
    for index, episode_sequence in enumerate(episode_sequences):
        episode_elements = episode_sequence.find_all("a", class_="portrait-element block-link titlefix episode")
        urls = [ "https://www.crunchyroll.com" + episode_element["href"] for episode_element in episode_elements]
        res.append(urls)

    # Sort result (should be sorted already)
    ep_number_regex = re.compile(r"(?<=\/episode-)(\d*)(\.){0,1}(\d*)(?=-)")
    for urls in res:
        # Crunchyroll default sorts by newest, sorting is faster this way
        urls.sort(key=lambda x: int("".join(re.findall(ep_number_regex, x)[0])), reverse=True)
        # Reverse so episode 1 is first
        urls.reverse()

    return res

def get_path(file_names=[], use_filedialog=False, sys_path=False, msg=None):
    for file_name in file_names:
        # Check if file is in the same directory as this script
        if os.path.isfile(os.path.join(os.path.dirname(__file__), file_name)):
            return os.path.join(os.path.dirname(__file__), file_name)
        
        if sys_path:
            # Check if ffmpeg is in system PATH
            file_path = which(file_name)
            if file_path and os.access(os.path.normpath(file_path), os.X_OK):
                return os.path.normpath(file_path)

    if not use_filedialog:
        if not msg:
            msg = f'Please enter the path to "{file_names[0]}"> '
        return os.path.normpath(input(msg).replace('"', '').replace("'", ""))
    else:
        return filedialog.askopenfilename(title = file_names[0])

def flattened_list(data):
    "Flatten list, maintaining it's order"
    ret = []
    for element in data:
        if isinstance(element, list):
            ret.extend(flattened_list(element))
        else:
            ret.append(element)
    return ret


###########

if __name__ == "__main__":
    # Process Arguments
    arguments = sys_argv[1:]

    if "-h" in arguments or "--help" in arguments:
        print(""""-un": Username for Crunchyroll login
"-pw": Password for Crunchyroll login
'-t' : Threads to use for downloading
"-c" : Path to config file
"-v" : Verbosity [0 (Default) - 5]
"-nf": Don't use filedialog; Type in paths manually
"-h" : Show this help

"-<YouTube-DL option>" : You can use all youtube_dl.YoutubeDL options by just adding a leading "-" that can be found here: 
                         https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L116-L323
                         Note: "ffmpeg_location", "outtmpl", "username", "password" and "verbose" will get overwritten.
""")
        exit()

    if "-c" in arguments:
        config_path = arguments.pop(arguments.index("-c")+1)
        arguments.remove("-c")
        if not os.path.isfile(config_path):
            config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    else:
        config_path = os.path.join(os.path.dirname(__file__), "config.yml")

    # Read config
    try:
        with open(config_path, "r") as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        if not "general" in config and "anime" in config:
            assert False
    except:
        config = {
            "general":{
                "ffmpeg_location": None,
                "filedialog": None
                },
            "anime": {},
            "sessions": []
            }

    # Process Arguments #2
    if "-un" in arguments:
        config["general"]["username"] = arguments.pop(arguments.index("-un")+1)
        arguments.remove("-un")
    else:
        config["general"]["username"] = None

    if "-t" in arguments:
        config["general"]["max_dl_threads"] = int(arguments.pop(arguments.index("-t")+1))
        arguments.remove("-t")
    else:
        config["general"]["max_dl_threads"] = 10
    
    if "-pw" in arguments:
        config["general"]["password"] = arguments.pop(arguments.index("-pw")+1)
        arguments.remove("-pw")
    else:
        config["general"]["password"] = None
    
    if "-v" in arguments:
        verbosity = int(arguments.pop(arguments.index("-v")+1))
        arguments.remove("-v")
    else:
        verbosity = 1

    if "-nf" in arguments:
        arguments.remove("-nf")
        use_filedialog = False
    else:
        try:
            from tkinter import Tk, filedialog
            use_filedialog = True

            # Create and hide Tkinter window
            root = Tk()
            root.withdraw()  

        except Exception as e:
            print(str(e), "\nFalling back to manual input\n")
            use_filedialog = False
         
    # Locate ffmpeg
    # Check if ffmpeg path is in config file and valid
    if not config["general"]["ffmpeg_location"] or not os.path.isfile(config["general"]["ffmpeg_location"]):
        if os.name != "nt":
            config["general"]["ffmpeg_location"] = get_path(["ffmpeg"],  use_filedialog, sys_path=True, msg="Please enter the path of the ffmpeg executable > ")
        else:
            config["general"]["ffmpeg_location"] = get_path(["ffmpeg.exe"], use_filedialog, sys_path=True, msg="Please enter the path of the ffmpeg executable > ")

    anime = []

    # Add new anime object to anime list; define the new entry as working anime
    anime.append(Anime())
    w_anime = anime[-1]

    # Process YTDL options
    for index, argument in enumerate(arguments):
        if "-" in argument:
            w_anime.config["custom"].update({argument: arguments[index+1]})

    # Load some configuration from global into Anime instance
    w_anime.config["ffmpeg_location"] = config["general"]["ffmpeg_location"]
    w_anime.config["password"] = config["general"]["password"]
    w_anime.config["username"] = config["general"]["username"]
    if "downloaded" not in w_anime.config:
        w_anime.config["downloaded"] = []

    # Restore unfinished sessions
    if "sessions" in config:
        if config["sessions"]:
            for i, j in enumerate(config["sessions"]):
                temp = PrettyTable(["ID", "Anime", "Episodes"])
                temp.add_row([i, *j])
            print("You've got some unfinished downloads:\n", temp)
            session_id = input("If you want to continue one, enter its ID > ")

    if config["sessions"] and session_id != "":
        session = config["sessions"][int(session_id)]
        w_anime.config = config["anime"][session[0]]
        dl_index = session[1]

    # If there are no sessions to restore or none was selected
    else:
        # Choose anime
        
        temp = PrettyTable(["ID", "Anime"])
        for number, name in enumerate(config["anime"]):
            temp.add_row([number, name])
        print(temp)
        choice = input("Choose an anime by entering it's ID or enter a URL > ")

        # If user entered a URL
        if not choice.isnumeric():
            w_anime.config["url"] = remove_lang_tag(choice)

            # Check if at least one episode is available
            while(True):
                w_anime.get_info()
                
                error = True
                for video_dict in w_anime.config["videos"].values():
                    if not "error" in video_dict.keys():
                        error = False
                        break

                if error:
                    w_anime.print_info()
                    if input("Try again? (y/N) > ").upper() != "Y":
                        exit()
                else:
                    break
            
            # Save w_anime.get_info() results 
            save_config()

        else:
            choice = int(choice)
            # Restore config of chosen anime
            w_anime.config = config["anime"][list(config["anime"])[choice]]


        # Check if output path is set and valid
        if not "output" in w_anime.config or not w_anime.config["output"] or not os.path.isdir(os.path.dirname(w_anime.config["output"])):

            # Choose download folder
            if not use_filedialog:
                download_path =  os.path.normpath(input("Choose a download folder > ").replace('"', '').replace("'", ""))
            else:
                download_path = filedialog.askdirectory(title = "Download folder")

            # Choose output syntax
            temp = input("Type in output syntax; Leave blank for default > ")
            if temp:
                output_syntax = temp
            else:
                output_syntax = "[%(playlist_index)s] %(series)s - S%(season_number)sE%(episode_number)s - %(episode)s.%(ext)s"

            # Compile to path
            w_anime.config["output"] = os.path.join(download_path, output_syntax)

            # Save updated output path
            save_config()

        # Show episode info
        w_anime.print_info()

        # Episodes to download
        print("Videos downloaded:", w_anime.config["downloaded"])
        temp = input("Videos to download > ")
        if temp:
            dl_index = []
            for i in temp.split(","):
                dl_index.extend(list(range(int(i.split("-")[0]), int(i.split("-")[1])+1)) if "-" in i else [int(i)])
        else:
            print("\nNo Video specified.. Exiting")
            exit()
            
        # Save session
        if [w_anime.config["title"], dl_index] not in config["sessions"]:
            config["sessions"].append([w_anime.config["title"], dl_index])
            save_config()

    # Download
    w_anime.config["verbosity"] = verbosity
    w_anime.max_dl_threads = config["general"]["max_dl_threads"]
    w_anime.start_download(dl_index)
    for thread in concurrent.futures.as_completed(w_anime.dl_threads):
        pass

    # Remove current session and add downloaded episodes to list
    del config["sessions"][-1]
    for index in dl_index:
        w_anime.config["downloaded"].append(index) if index not in w_anime.config["downloaded"] else None
    save_config()

    # Save config
    config["anime"][w_anime.config["title"]] = w_anime.config
    with open(config_path, "w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)
