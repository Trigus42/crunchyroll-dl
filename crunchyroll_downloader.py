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
                print("""Error: 'pip' not installed.""")

###########

if __name__ == '__main__':
    try:
        import youtube_dl
        import yaml
        from prettytable import PrettyTable
    except ModuleNotFoundError:
        print('Required modules: "youtube_dl", "PyYAML", "PrettyTable"')
        if input("Do you want to install them now? (y/N): ").upper() == "Y":
            install(["youtube_dl", "PyYAML", "PrettyTable"])
        if not sys_argv[1:]:
            input("Done")
        exit()
else:
    import youtube_dl
    import yaml
    from prettytable import PrettyTable

###########

class Anime():
    def __init__(self):
        self.config = {}
        self.ytdl_opts = {'quiet': True}
        self.verbosity = 0
        self.dl_episodes = []
        self.username = None
        self.password = None

    class Logger(object):
        def __init__(self, verbosity):
            self.verbosity = verbosity
            self.output = ""

        def debug(self, msg):
            self.output += msg
            if self.verbosity >= 2:
                print(msg)

        def warning(self, msg):
            if self.verbosity >= 1:
                print(msg)

        def error(self, msg):
            if self.verbosity >= 1:
                print(msg)

    def info(self):
        pl_info_opts = {
        "playlist_items":"0",
        "username": self.username,
        "password": self.password,
        "logger": self.Logger(self.verbosity),
        "verbose": True if self.verbosity >= 3 else False,
        "simulate": True
        }
        ep_info_opts = {
        "playlist_items": None,
        "username": self.username,
        "password": self.password,
        "logger": self.Logger(self.verbosity),
        "verbose": True if self.verbosity >= 3 else False
        }

        #Get total episode count
        try:
            youtube_dl.YoutubeDL(pl_info_opts).download([self.config["url"]])
        except youtube_dl.utils.DownloadError as e:
            if str(e) == "ERROR: Unable to download webpage: HTTP Error 403: Forbidden (caused by <HTTPError 403: 'Forbidden'>); please report this issue on https://yt-dl.org/bug . Make sure you are using the latest version; see  https://yt-dl.org/update  on how to update. Be sure to call youtube-dl with the --verbose flag and include its complete output.":
                return "ERROR: (HTTP 403) Forbidden"
            else:
                return e

        output = pl_info_opts["logger"].output
        self.config["total_episodes"] = int(output[output.find(": Collected ")+len(": Collected "):output.find(" video ids (downloading 1 of them)", output.find(": Collected "))])

        #Skip rest of function if anime is not available
        if self.config["total_episodes"] == 0:
            return "ERROR: Not Available"

        #Get info dict for every episode
        def ep_info(opts, url):
            try:
                ep_number = int(opts["playlist_items"]) #Save this variable since 'opts' changes for some reason
                return {ep_number: youtube_dl.YoutubeDL(opts).extract_info(url, download=False)}
            except youtube_dl.utils.DownloadError as e:
                return {ep_number: str(e)}

        self.unavailable_episodes = {}
        self.info_dict = {}
        threads = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config["total_episodes"]) as executor:
            for i in range(1, self.config["total_episodes"]+1):
                ep_info_opts["playlist_items"] = str(i)
                thread = executor.submit(ep_info, ep_info_opts, self.config["url"])
                threads.append(thread)

        for i in concurrent.futures.as_completed(threads, timeout=15):
            result = i.result()
            if isinstance(next(iter(result.values())), str):
                #Add unavailable episode numbers and exception to dictionary
                self.unavailable_episodes.update(result)
            elif not self.info_dict:
                self.info_dict = next(iter(result.values()))
            else:
                self.info_dict["entries"].extend(next(iter(result.values()))["entries"])

        #Episode info
        self.config["playlist_info"] = {}
        for i in self.info_dict["entries"]:
            self.config["playlist_info"].update({int(i["playlist_index"]): {"Season": i["season_number"], "Episode": i["episode_number"], "Language": i["formats"][0]['language']}})

        self.config["name"] = self.info_dict.get("title")

    def download(self, ffmpeg_location):
        self.ytdl_opts.update({
            "ffmpeg_location": ffmpeg_location,
            "outtmpl": path.join(self.config["download_path"], self.config["output_syntax"]),
            "username": self.username,
            "password": self.password,
            "verbose": True if self.verbosity >= 3 else False
            })

        def hook(d):
            if d['status'] == 'finished':
                print('Finished Video', self.ytdl_opts["playlist_items"])

        def run(url, ytdl_opts, playlist_index, logger, hook):
            ytdl_opts.update({'logger': logger, 'progress_hooks': [hook]})
            ytdl_opts["playlist_items"] = str(playlist_index)

            youtube_dl.YoutubeDL(ytdl_opts).download([url])

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.dl_episodes)) as executor:
            self.dl_threads = [executor.submit(run, w_anime.config["url"], self.ytdl_opts, playlist_index, self.Logger(self.verbosity), hook) for playlist_index in self.dl_episodes]

###########

if __name__ == '__main__':

    #Process Arguments
    arguments = sys_argv[1:]

    if "-h" in arguments or "--help" in arguments:
        print(''''-un': Username for Crunchyroll login
'-pw': Password for Crunchyroll login
'-c' : Path to config file
'-v' : Verbosity [0 (Default) - 3]
'-nf': Don't use filedialog; Type in paths manually
'-h' : Show this help

'-<YouTube-DL option>' : You can use all youtube_dl.YoutubeDL options by just adding a leading "-" that can be found here: 
                         https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L116-L323
                         Note: 'ffmpeg_location', 'outtmpl', 'username', 'password' and 'verbose' will get overwritten.
''')
        exit()

    if "-c" in arguments:
        config_path = arguments.pop(arguments.index("-c")+1)
        arguments.remove("-c")
        if not path.isfile(config_path):
            config_path = path.join(path.dirname(__file__), 'config.yml')
    else:
        config_path = path.join(path.dirname(__file__), 'config.yml')

    #Read config
    try:
        with open(config_path, 'r') as config_file:
            config = yaml.load(config_file, Loader=yaml.FullLoader)
        print("Found config file")
    except:
        config = {
            "general":{
                "ffmpeg_location": None,
                "filedialog": None
                },
            "anime":{
                }
            }

    #Process Arguments #2
    if "-un" in arguments:
        config["general"]["username"] = arguments.pop(arguments.index("-un")+1)
        arguments.remove("-un")
    else:
        config["general"]["username"] = None
    
    if "-pw" in arguments:
        config["general"]["password"] = arguments.pop(arguments.index("-pw")+1)
        arguments.remove("-pw")
    else:
        config["general"]["password"] = None
    
    if "-v" in arguments:
        verbosity = int(arguments.pop(arguments.index("-v")+1))
        arguments.remove("-v")
    else:
        verbosity = 0

    if "-nf" in arguments:
        arguments.remove("-nf")
        no_filedialog = True
    else:
        no_filedialog = False

    #Hide Tkinter window
    root = Tk()
    root.withdraw()   
        
    #Locate ffmpeg executable
    if not config["general"]["ffmpeg_location"] or not path.isfile(config["general"]["ffmpeg_location"]):
        if path.isfile(path.join(path.dirname(__file__), 'ffmpeg.exe')):
            config["general"]["ffmpeg_location"] = path.join(path.dirname(__file__), 'ffmpeg.exe')
        elif no_filedialog:
            config["general"]["ffmpeg_location"] = input("Enter the path of the ffmpeg executable > ")
        else:
            config["general"]["ffmpeg_location"] = filedialog.askopenfilename(title = "ffmpeg")

    anime = []

    #Add new anime object to anime list; define the new entry as working anime
    anime.append(Anime())
    w_anime = anime[-1]

    w_anime.password = config["general"]["password"]
    w_anime.username = config["general"]["username"]
    w_anime.verbosity = verbosity
    w_anime.config["downloaded"] = []

    #Choose anime
    print("Choose an anime or enter a URL:")
    for number, name in zip(range(len(config["anime"])), config["anime"]):
        print(f"{number}. {name}")
    choice = input("> ")

    if not choice.isnumeric():
        w_anime.config["url"] = choice

        #Get infos about the anime
        while(True):
            info_return = w_anime.info()
            if info_return:
                print(info_return)
                if input("Try again? (y/N) > ").upper() != "Y":
                    exit()
            else:
                break

        #Choose download folder
        if not filedialog:
            w_anime.config["download_path"] = input("Choose a download folder > ")
        else:
            w_anime.config["download_path"] = filedialog.askdirectory(title = "Download folder")

        #Choose output syntax
        temp = input("Type in output syntax; Leave blank for default > ")
        if temp:
            w_anime.config["output_syntax"] = temp
        else:
            w_anime.config["output_syntax"] = "[%(playlist_index)s] %(series)s - S%(season_number)sE%(episode_number)s - %(episode)s.%(ext)s"
    else:
        choice = int(choice)
        w_anime.config = config["anime"][list(config["anime"])[choice]]

    #Process YTDL options
    w_anime.config["advanced"] = {
    "postprocessors": [{'key': 'FFmpegEmbedSubtitle'}],
    "ignoreerrors": True,
    "nooverwrites": True,
    "allsubtitles": True,
    "writesubtitles": True
    }
    n = 0
    for i in arguments:
        if "-" in i:
            w_anime.config["advanced"][i[i.index("-")+1:]] = arguments[n+1]
        n+=1

    #More config
    w_anime.ytdl_opts.update(w_anime.config["advanced"])

    #Show episode info
    temp = PrettyTable(["Playlist Index", "Season", "Episode", "Language"])
    for i in sorted(w_anime.config["playlist_info"]):
        temp.add_row([i, w_anime.config["playlist_info"][i]["Season"], w_anime.config["playlist_info"][i]["Episode"],  w_anime.config["playlist_info"][i]["Language"]])
    
    print(temp)

    #Episodes to download
    print("Videos downloaded:", w_anime.config["downloaded"])
    temp = input(f'''Videos to download > ''')
    for i in temp.split(","):
        w_anime.dl_episodes.extend(list(range(int(i.split("-")[0]), int(i.split("-")[1])+1)) if "-" in i else [int(i)])
    for i in w_anime.dl_episodes:
        w_anime.config["downloaded"].append(i) if i not in w_anime.config["downloaded"] else None

    w_anime.download(config["general"]["ffmpeg_location"])

    #Save config
    config["anime"][w_anime.config["name"]] = w_anime.config
    with open(config_path), 'w') as config_file:
        yaml.dump(config, config_file, default_flow_style=False)
