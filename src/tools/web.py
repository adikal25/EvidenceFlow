# fetch implementation
import time, random, requests
from urllib import robotparser
from urllib.parse import urlparse

UA = "AgentStack/0.1 (+research)"

def allow_fetch(url: str) -> bool:
    p = urlparse(url)
    robots = f"{p.scheme}://{p.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(robots); rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True

def fetch(url: str, timeout: int = 10, sleep_window=(1.0,1.5)) -> str:
    if not allow_fetch(url):
        raise PermissionError(f"robots.txt disallows: {url}")
    time.sleep(random.uniform(*sleep_window))
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    return r.text
