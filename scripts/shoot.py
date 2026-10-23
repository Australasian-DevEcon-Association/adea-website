"""Dev-only: render page screenshots with headless Chrome for visual QA."""
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = os.path.join(os.environ["USERPROFILE"], "tmp", "chrome-shot-profile")
SHOTS = os.path.join(ROOT, "shots")
os.makedirs(SHOTS, exist_ok=True)

PAGES = [
    ("_site/index.html", "home.png", 2600),
    ("_site/about.html", "about.png", 1900),
    ("_site/news.html", "news.png", 1900),
    ("_site/news/welcome.html", "welcome.png", 1800),
    ("_site/members.html", "members.png", 3200),
    ("_site/stories.html", "stories.png", 1400),
]

for rel, out, h in PAGES:
    url = "file:///" + os.path.join(ROOT, rel).replace("\\", "/")
    dst = os.path.join(SHOTS, out)
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=1", f"--window-size=1440,{h}",
        "--run-all-compositor-stages-before-draw", "--virtual-time-budget=3000",
        "--force-prefers-reduced-motion=reduce",
        f"--user-data-dir={PROFILE}", f"--screenshot={dst}", url,
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    size = os.path.getsize(dst) if os.path.exists(dst) else 0
    print(f"{out:14s} {size/1024:7.1f} KB")
