"""
common.py — logique partagée avec AllDown desktop (détection de plateforme,
validation de lien, formatage des tailles/vitesses/temps restant).
"""

from urllib.parse import urlparse

PLATFORM_HINTS = [
    (("youtube.com", "youtu.be"), "YouTube"),
    (("tiktok.com",), "TikTok"),
    (("facebook.com", "fb.watch"), "Facebook"),
    (("instagram.com",), "Instagram"),
    (("twitter.com", "x.com"), "X / Twitter"),
    (("vimeo.com",), "Vimeo"),
    (("dailymotion.com",), "Dailymotion"),
    (("twitch.tv",), "Twitch"),
    (("reddit.com",), "Reddit"),
    (("soundcloud.com",), "SoundCloud"),
]


def is_supported_url(url: str) -> bool:
    url = (url or "").strip()
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return bool(parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc)
    except Exception:
        return False


def detect_platform(url: str) -> str:
    low = url.lower()
    for domains, label in PLATFORM_HINTS:
        if any(d in low for d in domains):
            return label
    return "Autre site"


def format_size(num_bytes):
    if not num_bytes:
        return "--"
    num_bytes = float(num_bytes)
    for unit in ["o", "Ko", "Mo", "Go", "To"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} Po"


def format_speed(bps):
    if not bps:
        return "--"
    return f"{format_size(bps)}/s"


def format_eta(seconds):
    if seconds is None:
        return "--"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h{m:02d}m{s:02d}s"
    return f"{m}m{s:02d}s"
