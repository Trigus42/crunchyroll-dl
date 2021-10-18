# crunchyroll-dl

This script uses the crunchyroll extractor from youtube-dl.  
It provides a CLI for downloading anime from Crunchyroll, displaying all videos with season, episode number and avaiable language.  
Most importantly it uses multithreading to significantly speed up everything.

### Quick-start

- Get ffmpeg
- Download this Repo
- Install requirements using `pip3 install -r requirements.txt`
- Start main.py

### Arguments:  
| Argument | Description |
|----------|----------|
| `-un` | Username for Crunchyroll login |
| `-pw` | Password for Crunchyroll login |
| `-t` | Threads to use for downloading; By default up to ten threads are used, however 4-6 threads will probably saturate an average connection. |
| `-c` | Path to config file |
| `-v` | Verbosity [0 (Default) - 5] |
| `-nf` | Don't use filedialog - Type in paths manually |
| `-h` | Show help |
| `-<YouTube-DL option>` | You can use all [youtube_dl.YoutubeDL](https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/YoutubeDL.py#L116-L323) options by just adding a leading hyphen |

### Troubleshooting:
- If items from a Playlist aren't shown, they are not available.
  This most likely happens because you need Crunchyroll premium to watch them or they are region-restricted.
- If you get the error "(HTTP 403) Forbidden" Crunchyroll rejected the request. This was most likely caused by IP blocking. Try a different VPN or renew your IP.

### Examples:
Download using 7 threads:
```
main.py -t 7
```

Only download subtitles:
```
main.py -skip_download True
```
