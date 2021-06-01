# crunchyroll-dl

**Currently not working because of issues with the extractor**

Tested with Python 3.9.1 and youtube-dl 2021.1.16  
Required Modules: 'youtube-dl', 'PyYAML', 'PrettyTable'

This program uses the crunchyroll extractor from youtube-dl.  
It provides a CLI for downloading anime from Crunchyroll, displaying all videos with season, episode number and avaiable language.  
Most importantly it uses multithreading to significantly speed up everything.

By default up to ten threads are used, however 4-6 threads will probably saturate an average connection.

### Arguments:  
'-un': Username for Crunchyroll login  
'-pw': Password for Crunchyroll login  
'-t' : Threads to use for downloading  
'-c' : Path to config file  
'-v' : Verbosity [0 (Default) - 5]  
'-nf': Don't use filedialog; Type in paths manually  
'-h' : Show help  

'-\<YouTube-DL option\>' : You can use all youtube_dl.YoutubeDL options by just adding a leading "-" that can be found here:  
                           https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L116-L323  
                           Note: 'ffmpeg_location', 'outtmpl', 'username', 'password' and 'verbose' will get overwritten.

### Troubleshooting:
- If items from a Playlist aren't shown, they are not available.
  This most likely happens because you need Crunchyroll premium to watch them or they are region-restricted.
- If you get the error "(HTTP 403) Forbidden" Crunchyroll rejected the request. This was most likely caused by IP blocking. Try a different VPN.

### Examples:
Download using 7 threads:
```
crunchyroll_downloader.py -t 7
```

Only download subtitles:
```
crunchyroll_downloader.py -skip_download True
```
