#!/usr/bin/env python3
"""Download each article's actual social thumbnail and optimize for the portfolio."""
from pathlib import Path
from urllib.parse import urljoin, urlparse
from html.parser import HTMLParser
from io import BytesIO
import requests
from PIL import Image, ImageOps, UnidentifiedImageError

ARTICLES = {
    "trinity_baba": "https://note.com/trinity_npi/n/n5dff04d83243",
    "trinity": "https://note.com/trinity_npi/n/n6c301bcaedff",
    "manga_mythology": "https://ndg.ac.jp/column/manga_mythology",
    "sotsuten_takeo": "https://npi.ac.jp/column/sotsuten_takeo",
    "emotionaldesign": "https://ndg.ac.jp/column/emotionaldesign",
    "natori_shasinnoyomikata1": "https://npi.ac.jp/column/natori_shasinnoyomikata1",
    "bauhaus": "https://ndg.ac.jp/column/bauhaus",
    "fwcomeback": "https://picon.fun/photo/20251120_fwcomeback/",
}
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WritingPortfolio/1.0; +https://github.com/shun1293/writing-portfolio)",
           "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*"}
class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.props = {}
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        d = dict(attrs)
        key = d.get("property") or d.get("name")
        if key and d.get("content"):
            self.props[key.lower()] = d["content"]

def download(session, url, referer=None):
    h = {"Referer": referer} if referer else {}
    response = session.get(url, timeout=35, headers=h)
    response.raise_for_status()
    if len(response.content) > 18_000_000:
        raise ValueError("Image too large")
    return response

def main():
    out = Path("images")
    out.mkdir(exist_ok=True)
    with requests.Session() as session:
        session.headers.update(HEADERS)
        failures = []
        for slug, page in ARTICLES.items():
            try:
                html = download(session, page).text
                parser = MetaParser()
                parser.feed(html)
                img_url = next((parser.props[k] for k in ("og:image", "twitter:image", "twitter:image:src") if parser.props.get(k)), None)
                if not img_url:
                    raise ValueError("No og:image or twitter:image")
                img_url = urljoin(page, img_url)
                data = download(session, img_url, page).content
                with Image.open(BytesIO(data)) as raw:
                    im = ImageOps.exif_transpose(raw).convert("RGB")
                    if im.width > 960:
                        height = round(im.height * 960 / im.width)
                        im = im.resize((960, height), Image.Resampling.LANCZOS)
                    target = out / (slug + ".webp")
                    im.save(target, "WEBP", quality=84, method=6)
                print(f"{slug}: {img_url} -> {target} ({target.stat().st_size//1024} KB)", flush=True)
            except Exception as ex:
                failures.append(f"{slug}: {type(ex).__name__}: {ex}")
        if failures:
            raise SystemExit("Thumbnail extraction failed:\n" + "\n".join(failures))
if __name__ == "__main__":
    main()
