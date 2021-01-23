from sys import exit, argv as sys_argv, executable as sys_executable
from os import path, name as os_name, system as os_system, _exit
from subprocess import check_call, CalledProcessError
import concurrent.futures
from tkinter import Tk, filedialog

###########

def install(packages):
    for package in packages:
        try:
            check_call([sys_executable, "-m", "pip", "install", "--user", package])
        except CalledProcessError:
            if os_name == "posix":
                os_system("sudo apt install python3-pip -y")
                check_call([sys_executable, "-m", "pip", "install", package])
            else:
                print("""Error: "pip" not installed.""")

###########

if __name__ == "__main__":
    try:
        import youtube_dl
        import yaml
        from prettytable import PrettyTable
    except ModuleNotFoundError:
        print("Required modules: 'youtube_dl', 'PyYAML', 'PrettyTable'")
        if input("Do you want to install them now? (y/N): ").upper() == "Y":
            install(["youtube_dl", "PyYAML", "PrettyTable"])
        if not sys_argv[1:]:
            input("\nDone")
        exit()
else:
    import youtube_dl

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
        for index, video_dict in enumerate(self.config["videos"]):
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

        # Get basic playlist info
        playlist_info = self.playlist_ie._real_extract(w_anime.config["url"])

        # Check which parts of the playlist are available to the user (to reduce requests)
        ## The playlist_info["entries"] list is sorted by language and season
        ## Each season / sequence of episodes in one language begins with "/episode-1-" in its URL
        if not self.check_all:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                threads = []
                for index, video_dict in enumerate(playlist_info["entries"]):
                    if "/episode-1-" in video_dict["url"]:
                        thread = executor.submit(self.video_info, index, video_dict["url"])
                        threads.append(thread)
                for thread in concurrent.futures.as_completed(threads):
                    result = thread.result()
                    playlist_info["entries"][result[0]].update(result[1])

        # Get detailed infos about the videos
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            threads = []
            skip_part = False
            for index, video_dict in enumerate(playlist_info["entries"]):
                # Skip because the info about the fist episodes of each section was already gathered (if self.check_all is False)
                if not self.check_all and "/episode-1-" in video_dict["url"]:
                    # If there has been an error, skip the rest of the section
                    skip_part = True if "error" in video_dict else False
                elif not skip_part:
                        thread = executor.submit(self.video_info, index, video_dict["url"])
                        threads.append(thread)
            for thread in concurrent.futures.as_completed(threads):
                result = thread.result()
                playlist_info["entries"][result[0]].update(result[1])
                if not "error" in result[1]:
                    del playlist_info["entries"][result[0]]["formats"][1:]

        # Save to config
        self.config.update({
            "title": playlist_info["title"],
            "id": playlist_info["id"],
            "videos": playlist_info["entries"],
        })

    def start_download(self, dl_index):
        self.update_config()

        dl_videos = [self.config["videos"][index] for index in dl_index]

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_dl_threads) as executor:
            for video_dict in dl_videos:
                thread = executor.submit(self._download, video_dict)
                self.dl_threads.append(thread)

    def _download(self, video_dict):
        # Create a new downloader object with copy of current config and self._hook as hook
        downloader = youtube_dl.YoutubeDL(self.ytdl_config.copy())
        downloader.params.update({"progress_hooks": [self._hook]})

        downloader.download([video_dict["url"]])

    def _hook(self, downloader):
            if downloader["status"] == "finished":
                print(f"Finished downloading ", path.basename(downloader["filename"]))

###########

if __name__ == "__main__":
    # Process Arguments
    arguments = sys_argv[1:]

    if "-h" in arguments or "--help" in arguments:
        print(""""-un": Username for Crunchyroll login
"-pw": Password for Crunchyroll login
"-c" : Path to config file
"-v" : Verbosity [0 (Default) - 3]
"-nf": Don"t use filedialog; Type in paths manually
"-h" : Show this help

"-<YouTube-DL option>" : You can use all youtube_dl.YoutubeDL options by just adding a leading "-" that can be found here: 
                        https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py# L116-L323
                        Note: "ffmpeg_location", "outtmpl", "username", "password" and "verbose" will get overwritten.
""")
        exit()

    if "-c" in arguments:
        config_path = arguments.pop(arguments.index("-c")+1)
        arguments.remove("-c")
        if not path.isfile(config_path):
            config_path = path.join(path.dirname(__file__), "config.yml")
    else:
        config_path = path.join(path.dirname(__file__), "config.yml")

    # Read config
    try:
        with open(config_path, "r") as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
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
        no_filedialog = True
    else:
        no_filedialog = False

    # Hide Tkinter window
    root = Tk()
    root.withdraw()   
        
    # Locate ffmpeg executable
    if not config["general"]["ffmpeg_location"] or not path.isfile(config["general"]["ffmpeg_location"]):
        if path.isfile(path.join(path.dirname(__file__), "ffmpeg.exe")):
            config["general"]["ffmpeg_location"] = path.join(path.dirname(__file__), "ffmpeg.exe")
        elif no_filedialog:
            config["general"]["ffmpeg_location"] = input("Enter the path of the ffmpeg executable > ")
        else:
            config["general"]["ffmpeg_location"] = filedialog.askopenfilename(title = "ffmpeg")

    anime = []

    # Add new anime object to anime list; define the new entry as working anime
    anime.append(Anime())
    w_anime = anime[-1]

    w_anime.config["ffmpeg_location"] = config["general"]["ffmpeg_location"]
    w_anime.config["password"] = config["general"]["password"]
    w_anime.config["username"] = config["general"]["username"]
    if "downloaded" not in w_anime.config:
        w_anime.config["downloaded"] = []

    if "sessions" in config:
        if config["sessions"]:
            for i, j in enumerate(config["sessions"]):
                temp = PrettyTable(["ID", "Anime", "Episodes"])
                temp.add_row([i, *j])
            print("You've got some unfinished downloads:\n", temp)
            session_id = input("If you want to continue one, enter its ID > ")

    if "session_id" in globals() and session_id != "":
        session = config["sessions"][int(session_id)]
        w_anime.config = config["anime"][session[0]]
        dl_index = session[1]
    else:
        # Choose anime
        print("Choose an anime or enter a URL:")
        for number, name in enumerate(config["anime"]):
            print(f"{number}. {name}")
        choice = input("> ")

        # If user entered a URL
        if not choice.isnumeric():
            w_anime.config["url"] = choice

            # Check if at least one episode is available
            while(True):
                w_anime.get_info()
                
                error = True
                for video_dict in w_anime.config["videos"]:
                    if not "error" in video_dict:
                        error = False

                if error:
                    w_anime.print_info()
                    if input("Try again? (y/N) > ").upper() != "Y":
                        exit()
                else:
                    break

            # Choose download folder
            if not filedialog:
                download_path = input("Choose a download folder > ")
            else:
                download_path = filedialog.askdirectory(title = "Download folder")

            # Choose output syntax
            temp = input("Type in output syntax; Leave blank for default > ")
            if temp:
                output_syntax = temp
            else:
                output_syntax = "[%(playlist_index)s] %(series)s - S%(season_number)sE%(episode_number)s - %(episode)s.%(ext)s"

            # Compile to path
            w_anime.config["output"] = path.join(download_path, output_syntax)

        else:
            choice = int(choice)
            w_anime.config = config["anime"][list(config["anime"])[choice]]

        # Process YTDL options
        for index, argument in enumerate(arguments):
            if "-" in argument:
                w_anime.config["custom"].update({argument: arguments[index+1]})

        # Show episode info
        w_anime.print_info()

        # Episodes to download
        print("Videos downloaded:", w_anime.config["downloaded"])
        temp = input("Videos to download > ")
        for i in temp.split(","):
            dl_index = list(range(int(i.split("-")[0]), int(i.split("-")[1])+1)) if "-" in i else [int(i)]

        # Save session
        if [w_anime.config["title"], dl_index] not in config["sessions"]:
            config["sessions"].append([w_anime.config["title"], dl_index])

        # Save config
        config["anime"].update({w_anime.config["title"]: w_anime.config})

        # Write to config file
        with open(config_path, "w") as config_file:
            yaml.dump(config, config_file, default_flow_style=False)

    # Download
    w_anime.config["verbosity"] = verbosity
    w_anime.max_dl_threads = config["general"]["max_dl_threads"]
    w_anime.start_download(dl_index)
    for thread in concurrent.futures.as_completed(w_anime.dl_threads):
        pass

    # Remove current session
    del config["sessions"][-1]
    for index in dl_index:
        w_anime.config["downloaded"].append(index) if index not in w_anime.config["downloaded"] else None

    # Save config
    config["anime"][w_anime.config["title"]] = w_anime.config
    with open(config_path, "w") as config_file:
        yaml.dump(config, config_file, default_flow_style=False)