import os
import re
import secrets
import time
import requests
import yt_dlp
from config import COOKIE_FILE_PATH

def download_tiktok_video(url):
    session_req = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/143.0.0.0 Mobile Safari/537.36",
        "Origin": "https://www.tikwm.com",
        "Referer": "https://www.tikwm.com/originalDownloader.html"
    }
    try:
        sub = session_req.post("https://www.tikwm.com/api/video/task/submit", data={"url": url, "web": "1"}, headers=headers, timeout=15)
        task_id = sub.json().get("data", {}).get("task_id")
        if not task_id:
            return None, None
        
        time.sleep(2)
        res = session_req.get("https://www.tikwm.com/api/video/task/result", params={"task_id": task_id}, headers=headers, timeout=15)
        detail = res.json().get("data", {}).get("detail", {})

        dl_url = detail.get("download_url", "")
        play_url = detail.get("play_url", "")

        if dl_url:
            rand = secrets.token_hex(8).upper()
            dl_url = re.sub(r'tikwm_[^/?&]+', f"MicroTools-{rand}.mp4", dl_url)
        if play_url:
            rand = secrets.token_hex(8).upper()
            play_url = re.sub(r'tikwm_[^/?&]+', f"MicroTools-{rand}.mp4", play_url)

        return dl_url, play_url or dl_url
    except Exception:
        return None, None

def extract_x_video_info(tweet_url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': COOKIE_FILE_PATH if os.path.exists(COOKIE_FILE_PATH) else None,
        'format': 'best[ext=mp4]/best'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(tweet_url, download=False)
        formats = info.get('formats', [])
        mp4_formats = [
            f for f in formats 
            if f.get('ext') == 'mp4' 
            and f.get('vcodec') != 'none' 
            and '.m3u8' not in f.get('url', '')
            and f.get('protocol') in ['http', 'https', None]
        ]
        if mp4_formats:
            selected = mp4_formats[-1]
            video_url = selected.get('url')
        else:
            video_url = info.get('url')
            selected = None
            for f in reversed(formats):
                if f.get('url') == video_url:
                    selected = f
                    break

        filesize = selected.get('filesize') or selected.get('filesize_approx') if selected else None
        if not filesize:
            filesize = info.get('filesize') or info.get('filesize_approx')

        size_str = f"{filesize / (1024 * 1024):.2f} MB" if filesize else ""
        return {
            'title': info.get('title', 'X Video'),
            'video_url': video_url,
            'filesize': size_str
        }
