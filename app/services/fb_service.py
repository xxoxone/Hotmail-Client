import re
import requests
from bs4 import BeautifulSoup
from config import FB_HEADERS

def format_proxy(raw_proxy):
    if not raw_proxy:
        return None
    raw = raw_proxy.strip()
    if not raw:
        return None
    if "://" not in raw:
        parts = raw.split(":")
        if len(parts) == 4:
            ip, port, user, pwd = parts
            return {
                "http": f"http://{user}:{pwd}@{ip}:{port}",
                "https": f"http://{user}:{pwd}@{ip}:{port}"
            }
        elif len(parts) == 2:
            ip, port = parts
            return {
                "http": f"http://{ip}:{port}",
                "https": f"http://{ip}:{port}"
            }
        else:
            return {
                "http": f"http://{raw}",
                "https": f"http://{raw}"
            }
    return {
        "http": raw,
        "https": raw
    }

def check_facebook_identity_precise(identifier, proxy=None):
    session_instance = requests.Session()
    proxies_dict = format_proxy(proxy)
    init_url = "https://limited.facebook.com/login/identify/?ctx=recover"
    base_url = "https://limited.facebook.com/login/identify/?ctx=recover&search_attempts=1&ars=facebook_login&alternate_search=0&show_friend_search_filtered_list=0&birth_month_search=0&city_search=0"
    
    try:
        req = session_instance.get(init_url, headers=FB_HEADERS, proxies=proxies_dict, timeout=12)
        soup = BeautifulSoup(req.text, 'html.parser')
        
        lsd = soup.find("input", {"name": "lsd"})
        jazoest = soup.find("input", {"name": "jazoest"})
        
        lsd_val = lsd.get("value", "") if lsd else ""
        jazoest_val = jazoest.get("value", "") if jazoest else ""
        
        payload = {
            "lsd": lsd_val,
            "jazoest": jazoest_val,
            "email": identifier,
            "did_submit": "Search"
        }
        
        res = session_instance.post(base_url, data=payload, headers=FB_HEADERS, proxies=proxies_dict, allow_redirects=True, timeout=12)
        page_soup = BeautifulSoup(res.text, 'html.parser')
        page_text = page_soup.get_text()
        
        not_found_str = "The phone number or email address that you've entered doesn't match an account"
        
        if not_found_str in page_text:
            return False
            
        if "login/identify" not in res.url or "recover/code" in res.url or "initiate_view" in res.text or "send_code" in res.text:
            return True
            
        return not_found_str not in page_text
    except Exception:
        return False

def extract_facebook_uid(share_url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    try:
        res = requests.get(share_url, headers=headers, allow_redirects=True, timeout=15)
        final_url, html = res.url, res.text
        patterns = [
            r'/people/[^/]+/(\d{10,})',
            r'profile\.php\?id=(\d{10,})',
            r'"userID":"(\d{10,})"',
            r'content="https://www\.facebook\.com/p/[^"]+-(\d{10,})/"',
            r'facebook\.com/(\d{10,})'
        ]
        for pattern in patterns:
            match = re.search(pattern, final_url) or re.search(pattern, html)
            if match:
                return match.group(1)
        return None
    except Exception:
        return None
