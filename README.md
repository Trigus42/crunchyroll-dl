# crunchyroll-dl
**CURRENTLY NOT WORKING RELIABLY**

Tested with Python 3.8.5 and youtube-dl 2020.9.20  
Required Modules: 'youtube-dl', 'PyYAML', 'PrettyTable'

This program uses the crunchyroll extractor from youtube-dl.  
It provides a CLI for downloading anime from Crunchyroll, displaying all videos with season, episode number and avaiable language.  
Most importantly it uses multithreading to significantly speed up everything.

### Arguments:  
'-un': Username for Crunchyroll login  
'-pw': Password for Crunchyroll login  
'-c' : Path to config file  
'-v' : Verbosity [0 (Default) - 3]  
'-nf': Don't use filedialog; Type in paths manually  
'-h' : Show help  

'-\<YouTube-DL option\>' : You can use all youtube_dl.YoutubeDL options by just adding a leading "-" that can be found here:  
                           https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L116-L323  
                           Note: 'ffmpeg_location', 'outtmpl', 'username', 'password' and 'verbose' will get overwritten.

### Troubleshooting:
- If items from a Playlist aren't in the table they are not available.
  This most likely happens because you need Crunchyroll premium to watch them.
- If you get the error "Not Available", the playlist returned by Crunchyroll was empty. This was most likely caused by region blocking. Maybe try using a VPN.
- If you get the error "(HTTP 403) Forbidden" Crunchyroll rejected the request. This was most likely caused by IP blocking. Try a different VPN.

### Examples:
Download subtitles:
```
crunchyroll_downloader.py -skip_download True
```
