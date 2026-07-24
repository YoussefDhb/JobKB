"""Web-scraping crawler (--scrape): a polite, bounded, fail-open crawler that snapshots raw job
postings to RESOURCES/SCRAPED/<lang>/<site>.csv. It never touches kb/ — ScraperSource ingests the
snapshot offline afterwards (see src/sources/scraper.py), so a crawl and a build are fully decoupled
and every build stays reproducible from the committed snapshot.

Per-site adapters are small dicts (listing URLs + a job-URL test); posting detail is read from the
page's schema.org JobPosting JSON-LD when present (robust across boards) with an HTML fallback. HTTP
is stdlib urllib with the same etiquette as the Wikidata client (descriptive UA, backoff, rate-limit,
broad fail-open) and robots.txt is honoured by default.
"""

from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser

from . import config as C
from . import common as K

_CHUNK = 20   # postings between snapshot checkpoints (resume granularity)


# --- HTTP (stdlib urllib; polite + resilient + fail-open) ------------------------------
def _http_get(url: str, encoding: str | None = None) -> str | None:
    """GET a page with retries/backoff. Returns the decoded body, or None on failure. `encoding` forces
    a charset (JSON APIs are UTF-8 per RFC 8259 but sometimes send a wrong header)."""
    delay = 1.0
    for attempt in range(C.SCRAPER_MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": C.SCRAPER_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=C.SCRAPER_TIMEOUT) as resp:
                charset = encoding or resp.headers.get_content_charset() or "utf-8"
                body = resp.read().decode(charset, "replace")
            time.sleep(C.SCRAPER_RATE_SLEEP)
            return body
        except Exception as e:  # noqa: BLE001 — HTTP/timeout/decode all fail-open (skip the page)
            code = getattr(e, "code", None)
            if code and 400 <= code < 500 and code != 429:
                return None  # a real 4xx won't improve on retry
            if attempt == C.SCRAPER_MAX_RETRIES - 1:
                return None
            time.sleep(delay)
            delay *= 2
    return None


_ROBOTS: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def _robot_ok(url: str) -> bool:
    """Honour robots.txt per host (fail-open: if robots can't be read, allow but stay polite)."""
    if not C.SCRAPER_RESPECT_ROBOTS:
        return True
    parts = urllib.parse.urlsplit(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host not in _ROBOTS:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(host + "/robots.txt")
        try:
            rp.read()
        except Exception:  # noqa: BLE001 — unreadable robots -> treat as unrestricted
            rp = None
        _ROBOTS[host] = rp
    rp = _ROBOTS[host]
    if rp is None:
        return True
    try:
        return rp.can_fetch(C.SCRAPER_USER_AGENT, url)
    except Exception:  # noqa: BLE001
        return True


# --- HTML parsing (JSON-LD JobPosting first, then a plain-text fallback) ----------------
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")


def _text_of(html: str) -> str:
    """Strip scripts/styles/tags to readable text (fallback when there is no JSON-LD)."""
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", html)
    txt = _TAG.sub(" ", html)
    txt = (txt.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
              .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&eacute;", "é"))
    txt = _WS.sub(" ", txt)
    return _NL.sub("\n\n", "\n".join(l.strip() for l in txt.splitlines())).strip()


def _jsonld_objects(html: str):
    """Yield every parsed application/ld+json object (flattening @graph and lists)."""
    for m in re.finditer(r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, list):
                stack.extend(obj)
            elif isinstance(obj, dict):
                if "@graph" in obj:
                    stack.extend(obj["@graph"] if isinstance(obj["@graph"], list) else [obj["@graph"]])
                yield obj


def _parse_detail(html: str, url: str) -> dict | None:
    """Return {title, location, text} for a posting page — JSON-LD JobPosting if present, else HTML."""
    for obj in _jsonld_objects(html):
        t = obj.get("@type")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            title = (obj.get("title") or "").strip()
            desc = _text_of(str(obj.get("description") or ""))
            loc = ""
            jl = obj.get("jobLocation")
            jl = jl[0] if isinstance(jl, list) and jl else jl
            if isinstance(jl, dict):
                addr = jl.get("address") or {}
                if isinstance(addr, dict):
                    loc = (addr.get("addressLocality") or addr.get("addressRegion") or "").strip()
            if title and desc:
                return {"title": title, "location": loc, "text": desc}
    # HTML fallback: <h1> as the title + the page text (best-effort).
    m = re.search(r"(?is)<h1[^>]*>(.*?)</h1>", html)
    title = _TAG.sub(" ", m.group(1)).strip() if m else ""
    text = _text_of(html)
    if title and len(text) > 200:
        return {"title": title, "location": "", "text": text[:8000]}
    return None


def _links(html: str, base: str):
    """Absolute hrefs found on a listing page (deduped, order-preserving)."""
    out, seen = [], set()
    for m in re.finditer(r'(?i)href=["\']([^"\'#]+)["\']', html):
        href = urllib.parse.urljoin(base, m.group(1).strip())
        if href not in seen:
            seen.add(href)
            out.append(href)
    return out


# --- API-mode adapter: RemoteOK ---------------------------------------------------------
# RemoteOK exposes a public JSON endpoint (its ToS explicitly permits API use, asking for a link back —
# we keep each posting's `url`). Robots-permitted, unlike the HTML boards. Used for the live test.
# Filter on the POSITION title (the feed's tag list is an unreliable soup on featured listings).
_IT_TITLE_HINTS = (
    "developer", "engineer", "programmer", "software", "devops", "sysadmin", "sre",
    "backend", "back-end", "back end", "frontend", "front-end", "front end", "full stack", "fullstack",
    "data scientist", "data engineer", "data analyst", "machine learning", " ml ", " ai ",
    "web develop", "mobile develop", "cloud", "cyber", "security engineer", "qa engineer",
    "platform engineer", "site reliability", "architect", "it support", "technical support",
)


def _demojibake(s: str) -> str:
    """Repair UTF-8 bytes that were double-encoded upstream (e.g. 'Ã§Ã£o' -> 'ção')."""
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def _remoteok(budget: int) -> list[dict]:
    """Fetch RemoteOK's public JSON feed, keep IT postings (by title), return snapshot rows (fail-open)."""
    url = "https://remoteok.com/api"
    if not _robot_ok(url):
        print(f"  [remoteok] robots.txt disallows {url} — skipping")
        return []
    raw = _http_get(url, encoding="utf-8")   # JSON is UTF-8 (RFC 8259); RemoteOK mislabels the charset
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    rows = []
    for j in data:
        if not isinstance(j, dict) or "position" not in j:   # skip the legal/meta header entry
            continue
        pos = " ".join(_demojibake(j.get("position") or "").split())   # collapse stray newlines/spaces
        if not any(h in f" {pos.lower()} " for h in _IT_TITLE_HINTS):
            continue
        text = _demojibake(_text_of(str(j.get("description") or "")))
        if not pos or len(text) < 120:
            continue
        rows.append({"site": "remoteok", "url": (j.get("url") or "").strip(), "lang": "en",
                     "title": pos, "location": _demojibake((j.get("location") or "").strip()),
                     "text": text, "retrieved_at": K.now_iso()})
        if len(rows) >= budget:
            break
    return rows


# --- per-site adapters -----------------------------------------------------------------
# HTML boards: lang, default IT `queries`, a `listing(query, page)` URL builder, and `is_job(url)` to
# pick posting-detail links (detail parsing is shared: JSON-LD + fallback). An API board instead sets
# `api(budget) -> rows`. Adding a board is usually just these few lines.
ADAPTERS = {
    "remoteok": {
        "lang": "en",
        "api": _remoteok,   # robots-permitted public JSON feed (the live-test source)
    },
    "hellowork": {
        "lang": "fr",
        "queries": ["developpeur", "data engineer", "devops", "cybersecurite"],
        "listing": lambda q, p: ("https://www.hellowork.com/fr-fr/emploi/recherche.html?k="
                                  f"{urllib.parse.quote(q)}&p={p}"),
        "is_job": lambda u: "/emplois/" in u and u.endswith(".html"),
    },
    "weworkremotely": {
        "lang": "en",
        "queries": [""],  # a category page (the query is unused); detail links carry a company-role slug
        "listing": lambda q, p: "https://weworkremotely.com/categories/remote-programming-jobs",
        "is_job": lambda u: ("/remote-jobs/" in u and u.count("-") >= 2
                             and not any(x in u for x in ("find-your-plan", "/search", "?", "#"))),
    },
}


def _crawl_site(site: str, budget: int) -> list[dict]:
    """Crawl one board up to `budget` postings; return snapshot rows (best-effort, fail-open)."""
    ad = ADAPTERS[site]
    if "api" in ad:                       # API board (RemoteOK): one JSON fetch, no listing/detail flow
        return ad["api"](budget)
    lang = ad["lang"]
    detail_urls, seen = [], set()
    for q in ad["queries"]:
        for p in range(1, C.SCRAPER_MAX_PAGES + 1):
            if len(detail_urls) >= budget:
                break
            url = ad["listing"](q, p)
            if not _robot_ok(url):
                print(f"  [{site}] robots.txt disallows {url} — skipping")
                continue
            html = _http_get(url)
            if not html:
                continue
            for href in _links(html, url):
                if ad["is_job"](href) and href not in seen:
                    seen.add(href)
                    detail_urls.append(href)
        if len(detail_urls) >= budget:
            break

    rows = []
    for url in detail_urls[:budget]:
        if not _robot_ok(url):
            continue
        html = _http_get(url)
        if not html:
            continue
        rec = _parse_detail(html, url)
        if not rec:
            continue
        rows.append({
            "site": site, "url": url, "lang": lang,
            "title": rec["title"], "location": rec["location"],
            "text": rec["text"], "retrieved_at": K.now_iso(),
        })
    return rows


# --- snapshot I/O (append + dedup by url, checkpointed) --------------------------------
def _snapshot_path(site: str, lang: str) -> str:
    return os.path.join(C.SCRAPED_DIR, lang, f"{site}.csv")


def _load(path: str) -> dict:
    rows = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows[r["url"]] = r
    return rows


def _save(path: str, rows: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: r.get("retrieved_at", ""))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.SCRAPED_FIELDS)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r.get(k, "") for k in C.SCRAPED_FIELDS})


def fetch_live(site: str, limit: int | None = None) -> list[dict]:
    """Crawl one board over the network and RETURN the posting rows WITHOUT writing a snapshot — for a
    live, read-only test (e.g. the notebook). Robots-checked and fail-open like the full crawl."""
    if site not in ADAPTERS:
        raise ValueError(f"unknown scrape site '{site}'. Known: {', '.join(ADAPTERS)}")
    return _crawl_site(site, limit or C.SCRAPER_MAX_POSTINGS)


def run(sites: str = "all") -> None:
    """Crawl the requested boards (comma-list or 'all') and update their snapshots. Network, opt-in."""
    try:
        import bs4  # noqa: F401 — availability check; parsing itself is regex/JSON-LD based
    except ImportError:
        pass  # bs4 is listed in requirements for robustness but this crawler needs only the stdlib

    names = list(ADAPTERS) if sites in ("all", "", None) else [s.strip() for s in sites.split(",") if s.strip()]
    unknown = [s for s in names if s not in ADAPTERS]
    if unknown:
        raise SystemExit(f"unknown scrape site(s): {', '.join(unknown)}. Known: {', '.join(ADAPTERS)}")

    per_site = max(1, C.SCRAPER_MAX_POSTINGS // len(names))
    total_new = 0
    for site in names:
        lang = ADAPTERS[site]["lang"]
        path = _snapshot_path(site, lang)
        existing = _load(path)
        print(f"[scrape] {site}: {len(existing)} cached postings; crawling up to {per_site} more…")
        got = _crawl_site(site, per_site)
        added = 0
        for i, row in enumerate(got, 1):
            if row["url"] not in existing:
                added += 1
            existing[row["url"]] = row
            if i % _CHUNK == 0:
                _save(path, existing)   # checkpoint (resumable)
        _save(path, existing)
        total_new += added
        print(f"[scrape] {site}: +{added} new (snapshot now {len(existing)}) -> {path}")

    print(f"[scrape] done: {total_new} new postings across {len(names)} site(s). "
          f"Run `python run_pipeline.py --add SCRAPER` to ingest them.")
