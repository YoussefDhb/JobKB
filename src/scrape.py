"""Web-scraping acquisition layer (--scrape): a polite, bounded, fail-open crawler that snapshots raw IT
job postings + emerging-tech signals to RESOURCES/SCRAPED/<lang>/<adapter>.csv. It never touches kb/ —
ScraperSource ingests the snapshot offline afterwards (src/sources/scraper.py), so acquisition and build
are decoupled and every build stays reproducible from the committed snapshot.

Three tiers, all normalising to the same SCRAPED_FIELDS row and passing the IT-title filter:
  * apis   — keyless job APIs (Jobicy, Remotive, RemoteOK, The Muse, We Work Remotely RSS); several give a
             pre-extracted `tags[]` skill array (a high-precision signal, like data_jobs' job_skills).
  * ats    — public Applicant-Tracking-System job boards (Greenhouse / Ashby / Lever) over a curated,
             self-healing company-token list; full job-description HTML, reliable structured JSON.
  * trends — emerging-tech signals (HN "Who is hiring", GitHub topics, Stack Overflow popular tags).

HTTP is stdlib urllib with the wikidata client's etiquette (descriptive UA, backoff, rate-limit, broad
fail-open). robots.txt is honoured for the RSS feed. Attribution: each row keeps its source `url` (link
back) — several sources' ToS require crediting them.
"""

from __future__ import annotations

import csv
import datetime as _dt
import gzip
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.robotparser

from . import config as C
from . import common as K

_CHUNK = 40   # postings between snapshot checkpoints (resume granularity)


# --- HTTP (stdlib urllib; polite + resilient + fail-open) ------------------------------
def _http_get(url: str, encoding: str | None = None, headers: dict | None = None) -> str | None:
    """GET a page with retries/backoff. Returns the decoded body (gzip-aware), or None on failure."""
    delay = 1.0
    hdrs = {"User-Agent": C.SCRAPER_USER_AGENT,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            "Accept-Language": "en,fr;q=0.8"}
    if headers:
        hdrs.update(headers)
    for attempt in range(C.SCRAPER_MAX_RETRIES):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs),
                                        timeout=C.SCRAPER_TIMEOUT) as resp:
                raw = resp.read()
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                charset = encoding or resp.headers.get_content_charset() or "utf-8"
            time.sleep(C.SCRAPER_RATE_SLEEP)
            return raw.decode(charset, "replace")
        except Exception as e:  # noqa: BLE001 — HTTP/timeout/decode all fail-open (skip the page)
            code = getattr(e, "code", None)
            if code and 400 <= code < 500 and code != 429:
                return None  # a real 4xx (incl. 403 rate-limit / 404 dead token) won't improve on retry
            if attempt == C.SCRAPER_MAX_RETRIES - 1:
                return None
            time.sleep(delay)
            delay *= 2
    return None


def _get_json(url: str, headers: dict | None = None):
    """GET + parse JSON (UTF-8). Returns the object, or None on any failure (fail-open)."""
    raw = _http_get(url, encoding="utf-8", headers=headers)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


_ROBOTS: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def _robot_ok(url: str) -> bool:
    """Honour robots.txt per host (fail-open: unreadable robots -> allow but stay polite)."""
    if not C.SCRAPER_RESPECT_ROBOTS:
        return True
    parts = urllib.parse.urlsplit(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host not in _ROBOTS:
        # Fetch robots.txt with OUR real UA (RobotFileParser.read() uses a bare Python UA that some CDNs
        # 403 -> it would then set disallow_all and falsely block a permitted path). Unreadable -> allow.
        body = _http_get(host + "/robots.txt")
        rp = None
        if body is not None:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.parse(body.splitlines())
            except Exception:  # noqa: BLE001
                rp = None
        _ROBOTS[host] = rp
    rp = _ROBOTS[host]
    if rp is None:
        return True
    try:
        return rp.can_fetch(C.SCRAPER_USER_AGENT, url)
    except Exception:  # noqa: BLE001
        return True


# --- text normalisation ----------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_NL = re.compile(r"\n{3,}")

# A posting is kept only if its (cleaned) title reads as an IT role — every API's server-side category
# filter leaks non-IT jobs, so this client-side gate is essential.
_IT_TITLE_HINTS = (
    "developer", "engineer", "programmer", "software", "devops", "sysadmin", "sre", "data scientist",
    "data engineer", "data analyst", "machine learning", "backend", "back-end", "back end", "frontend",
    "front-end", "front end", "full stack", "fullstack", " ml ", " ai ", "web develop", "mobile develop",
    "cloud", "cyber", "security engineer", "qa engineer", "qa tester", "test engineer", "platform engineer",
    "site reliability", "architect", "it support", "technical support", "database admin", "network engineer",
    "system administrator", "systems administrator", "analytics", "blockchain", "ux engineer",
)


def _demojibake(s: str) -> str:
    """Repair UTF-8 bytes that were double-encoded upstream (e.g. 'Ã§Ã£o' -> 'ção')."""
    if "Ã" in s or "Â" in s:
        try:
            return s.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def _clean(s: str) -> str:
    """Collapse whitespace + repair double-encoding on a short field (title/company/location)."""
    return " ".join(_demojibake(s or "").split())


def _text_of(fragment: str) -> str:
    """Strip HTML tags/entities to readable text (job descriptions arrive as HTML)."""
    t = html.unescape(fragment or "")
    t = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", t)
    t = _TAG.sub(" ", t)
    t = _WS.sub(" ", _demojibake(t))
    return _NL.sub("\n\n", "\n".join(l.strip() for l in t.splitlines())).strip()


def _is_it_title(title: str) -> bool:
    return any(h in f" {title.lower()} " for h in _IT_TITLE_HINTS)


def _row(site, url, lang, title, company, location, text, tags, posted_at) -> dict:
    return {"site": site, "url": (url or "").strip(), "lang": lang,
            "title": _clean(title), "company": _clean(company), "location": _clean(location),
            "text": text, "tags": (tags or "").strip(), "posted_at": (posted_at or "").strip(),
            "retrieved_at": K.now_iso()}


def _dedup_url(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        u = r.get("url")
        if u and u not in seen:
            seen.add(u)
            out.append(r)
    return out


def _tags(seq) -> str:
    return "|".join(str(t).strip() for t in (seq or []) if str(t).strip())


# ========================= Tier A — keyless job APIs ===================================
def _jobicy(budget):
    rows = []
    for ind in C.JOBICY_INDUSTRIES:
        if len(rows) >= budget:
            break
        d = _get_json(f"https://jobicy.com/api/v2/remote-jobs?count={C.SCRAPER_MAX_PER_QUERY}&industry={ind}")
        for j in (d or {}).get("jobs", []):
            title = _clean(j.get("jobTitle", ""))
            text = _text_of(str(j.get("jobDescription") or ""))
            if not _is_it_title(title) or len(text) < 120:
                continue
            rows.append(_row("jobicy", j.get("url"), "en", title, j.get("companyName"),
                             j.get("jobGeo"), text, "", j.get("pubDate")))
    return _dedup_url(rows)[:budget]


def _remotive(budget):
    # One call (its ToS caps to ~2/min); filter to IT client-side. `tags[]` is a clean skill array.
    d = _get_json("https://remotive.com/api/remote-jobs?limit=200")
    rows = []
    for j in (d or {}).get("jobs", []):
        title = _clean(j.get("title", ""))
        text = _text_of(str(j.get("description") or ""))
        if not _is_it_title(title) or len(text) < 120:
            continue
        rows.append(_row("remotive", j.get("url"), "en", title, j.get("company_name"),
                         j.get("candidate_required_location"), text, _tags(j.get("tags")),
                         j.get("publication_date")))
        if len(rows) >= budget:
            break
    return _dedup_url(rows)


def _remoteok(budget):
    d = _get_json("https://remoteok.com/api")   # tech-first feed; UA must be browser-like (set in config)
    rows = []
    for j in d or []:
        if not isinstance(j, dict) or "position" not in j:      # skip the legal/meta header entry
            continue
        title = _clean(j.get("position", ""))
        text = _text_of(str(j.get("description") or ""))
        if not _is_it_title(title) or len(text) < 120:
            continue
        rows.append(_row("remoteok", j.get("url"), "en", title, j.get("company"),
                         j.get("location"), text, _tags(j.get("tags")), j.get("date")))
        if len(rows) >= budget:
            break
    return _dedup_url(rows)


def _themuse(budget):
    rows = []
    for cat in C.THEMUSE_CATEGORIES:
        for page in range(1, C.SCRAPER_MAX_PAGES + 1):
            if len(rows) >= budget:
                break
            d = _get_json("https://www.themuse.com/api/public/jobs?"
                          f"category={urllib.parse.quote(cat)}&page={page}")
            results = (d or {}).get("results", [])
            if not results:
                break
            for j in results:
                title = _clean(j.get("name", ""))
                text = _text_of(str(j.get("contents") or ""))
                if not _is_it_title(title) or len(text) < 120:
                    continue
                loc = ", ".join(l.get("name", "") for l in (j.get("locations") or []))
                url = (j.get("refs") or {}).get("landing_page", "")
                rows.append(_row("themuse", url, "en", title, (j.get("company") or {}).get("name"),
                                 loc, text, _tags(j.get("tags")), j.get("publication_date")))
    return _dedup_url(rows)[:budget]


def _rss_field(item, tag):
    m = re.search(rf"(?is)<{tag}[^>]*>(.*?)</{tag}>", item)
    if not m:
        return ""
    v = m.group(1).strip()
    return re.sub(r"(?is)^<!\[CDATA\[(.*?)\]\]>\s*$", r"\1", v).strip()


def _wwr(budget):
    rows = []
    for feed in C.WWR_FEEDS:
        if len(rows) >= budget:
            break
        url = f"https://weworkremotely.com/categories/{feed}.rss"
        if not _robot_ok(url):
            print(f"  [wwr] robots.txt disallows {url} — skipping")
            continue
        raw = _http_get(url)
        if not raw:
            continue
        for item in re.findall(r"(?is)<item>(.*?)</item>", raw):
            title_raw = html.unescape(_rss_field(item, "title"))
            company, sep, role = title_raw.partition(":")     # WWR titles are "Company: Role"
            title = _clean(role if sep else title_raw)
            text = _text_of(_rss_field(item, "description"))
            if not _is_it_title(title) or len(text) < 120:
                continue
            rows.append(_row("wwr", _rss_field(item, "link"), "en", title,
                             _clean(company) if sep else "", _rss_field(item, "region"),
                             text, "", _rss_field(item, "pubDate")))
            if len(rows) >= budget:
                break
    return _dedup_url(rows)


# ========================= Tier B — public ATS job boards ==============================
def _ms_to_iso(ms):
    try:
        return _dt.datetime.fromtimestamp(int(ms) / 1000, _dt.timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return ""


def _ats_board(provider, token, cap):
    """Fetch one company's public ATS board. Self-healing: a dead/empty token returns []."""
    rows = []
    if provider == "greenhouse":
        d = _get_json(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
        for j in (d or {}).get("jobs", []):
            title = _clean(j.get("title", ""))
            text = _text_of(str(j.get("content") or ""))
            if not _is_it_title(title) or len(text) < 120:
                continue
            rows.append(_row("ats:greenhouse", j.get("absolute_url"), "en", title, j.get("company_name") or token,
                             (j.get("location") or {}).get("name"), text, "",
                             j.get("updated_at") or j.get("first_published")))
            if len(rows) >= cap:
                break
    elif provider == "ashby":
        d = _get_json(f"https://api.ashbyhq.com/posting-api/job-board/{token}")
        for j in (d or {}).get("jobs", []):
            title = _clean(j.get("title", ""))
            text = _text_of(str(j.get("descriptionHtml") or j.get("descriptionPlain") or ""))
            if not _is_it_title(title) or len(text) < 120:
                continue
            rows.append(_row("ats:ashby", j.get("jobUrl") or j.get("applyUrl"), "en", title,
                             token.capitalize(), j.get("location"), text, "", j.get("publishedAt")))
            if len(rows) >= cap:
                break
    elif provider == "lever":
        d = _get_json(f"https://api.lever.co/v0/postings/{token}?mode=json")
        for j in d or []:
            title = _clean(j.get("text", ""))
            text = _text_of(str(j.get("descriptionPlain") or j.get("description") or ""))
            if not _is_it_title(title) or len(text) < 120:
                continue
            loc = (j.get("categories") or {}).get("location", "")
            rows.append(_row("ats:lever", j.get("hostedUrl"), "en", title, token.capitalize(),
                             loc, text, "", _ms_to_iso(j.get("createdAt"))))
            if len(rows) >= cap:
                break
    return rows


def _ats(budget):
    rows = []
    for provider, token in C.SCRAPER_ATS_BOARDS:
        if len(rows) >= budget:
            break
        try:
            got = _ats_board(provider, token, C.SCRAPER_ATS_MAX_PER_TOKEN)
        except Exception:  # noqa: BLE001 — one bad board never breaks the rest
            got = []
        if got:
            print(f"  [ats] {provider}:{token} -> {len(got)} IT postings")
        rows.extend(got)
    return _dedup_url(rows)[:budget]


# ========================= Tier C — emerging-tech trend signals ========================
def _hn_role(header):
    """Best-effort IT role from an HN 'Company | Role | Location | …' header line ("" if none)."""
    for seg in re.split(r"\s*[|•·—–]\s*|\s{2,}", header):
        seg = _clean(seg)
        if seg and _is_it_title(seg) and len(seg.split()) <= C.SCRAPER_TITLE_MAX_WORDS:
            return seg
    return ""


def _hn(budget):
    s = _get_json("https://hn.algolia.com/api/v1/search_by_date?"
                  "tags=story,author_whoishiring&query=who%20is%20hiring&hitsPerPage=15")
    story = None
    for h in (s or {}).get("hits", []):
        t = (h.get("title") or "").lower()
        if "who is hiring" in t and "freelanc" not in t and "wants to be hired" not in t:
            story = h.get("objectID")
            break
    if not story:
        return []
    item = _get_json(f"https://hn.algolia.com/api/v1/items/{story}")
    rows = []
    for ch in (item or {}).get("children", []) or []:
        if not ch.get("text"):
            continue
        text = _text_of(ch["text"])
        if len(text) < 120:
            continue
        title = _hn_role(text.split("\n", 1)[0])   # role if the header is a clear IT role, else skills-only
        rows.append(_row("hn", f"https://news.ycombinator.com/item?id={ch.get('id')}", "en",
                         title, "", "", text, "", ch.get("created_at")))
        if len(rows) >= budget:
            break
    return rows


_GH_STOP = {"awesome", "hacktoberfest", "productivity", "developer-tools", "open-source", "tutorial",
            "example", "boilerplate", "template", "list", "framework", "library", "cli", "api", "app"}


def _github(budget):
    """Emerging-tech topic tokens from fast-rising repos → tag-only candidate skills (gate-screened)."""
    headers = {"Authorization": f"Bearer {C.GITHUB_TOKEN}"} if C.GITHUB_TOKEN else None
    rows = []
    for topic in C.GITHUB_TREND_TOPICS:
        if len(rows) >= budget:
            break
        q = urllib.parse.quote(f"topic:{topic} stars:>{C.SCRAPER_TREND_MIN_STARS}")
        d = _get_json(f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=10",
                      headers=headers)
        for it in (d or {}).get("items", []):
            cand = {t for t in (it.get("topics") or []) if t not in _GH_STOP and len(t) > 1}
            if it.get("language"):
                cand.add(it["language"])
            if not cand:
                continue
            rows.append(_row("github", it.get("html_url"), "en", "", it.get("full_name"), "",
                             (it.get("description") or "")[:400], _tags(sorted(cand)), it.get("created_at")))
    return _dedup_url(rows)[:budget]


def _stackoverflow(budget):
    """Popular Stack Overflow technology tags → tag candidates (coverage / corroboration signal)."""
    d = _get_json("https://api.stackexchange.com/2.3/tags?site=stackoverflow&order=desc&sort=popular&pagesize=100")
    tags = [t.get("name") for t in (d or {}).get("items", []) if t.get("name")]
    if not tags:
        return []
    return [_row("stackoverflow", "https://stackoverflow.com/tags", "en", "", "Stack Overflow", "",
                 "Popular Stack Overflow technology tags (emerging-tech coverage signal).",
                 _tags(tags), "")]


# --- adapter registry ------------------------------------------------------------------
ADAPTERS = {
    "jobicy": _jobicy, "remotive": _remotive, "remoteok": _remoteok, "themuse": _themuse, "wwr": _wwr,
    "ats": _ats,
    "hn": _hn, "github": _github, "stackoverflow": _stackoverflow,
}


def _resolve_sites(sites: str) -> list[str]:
    """Expand 'all' / a tier name / a comma-list of tiers-or-adapters into adapter names."""
    if sites in ("all", "", None):
        return list(ADAPTERS)
    out = []
    for tok in (s.strip() for s in sites.split(",") if s.strip()):
        if tok in C.SCRAPER_TIERS:
            out.extend(C.SCRAPER_TIERS[tok])
        elif tok in ADAPTERS:
            out.append(tok)
        else:
            raise SystemExit(f"unknown scrape target '{tok}'. Tiers: {', '.join(C.SCRAPER_TIERS)}; "
                             f"adapters: {', '.join(ADAPTERS)}")
    seen, uniq = set(), []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq


def _crawl(name: str, budget: int) -> list[dict]:
    """Run one adapter, fail-open (a single source down never breaks the run)."""
    try:
        return ADAPTERS[name](budget) or []
    except Exception as e:  # noqa: BLE001
        print(f"  [{name}] error: {type(e).__name__}: {e} — skipped")
        return []


# --- snapshot I/O (append + dedup by url, retention prune, checkpointed) ----------------
def _snapshot_path(name: str) -> str:
    return os.path.join(C.SCRAPED_DIR, "en", f"{name.replace(':', '_')}.csv")


def _load(path: str) -> dict:
    rows = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("url"):
                    rows[r["url"]] = r
    return rows


def _prune_old(rows: dict) -> dict:
    """Drop snapshot rows whose retrieved_at is older than the retention window (keeps demand current)."""
    if C.SCRAPER_RETENTION_DAYS <= 0:
        return rows
    cutoff = (_dt.datetime.now(_dt.timezone.utc)
              - _dt.timedelta(days=C.SCRAPER_RETENTION_DAYS)).isoformat()
    return {u: r for u, r in rows.items() if (r.get("retrieved_at") or "") >= cutoff}


def _save(path: str, rows: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ordered = sorted(rows.values(), key=lambda r: r.get("retrieved_at", ""))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=C.SCRAPED_FIELDS)
        w.writeheader()
        for r in ordered:
            w.writerow({k: r.get(k, "") for k in C.SCRAPED_FIELDS})


def fetch_live(site: str, limit: int | None = None) -> list[dict]:
    """Crawl one adapter over the network and RETURN the rows WITHOUT writing a snapshot — for a live,
    read-only test (e.g. the notebook). Fail-open like the full crawl."""
    if site not in ADAPTERS:
        raise ValueError(f"unknown scrape adapter '{site}'. Known: {', '.join(ADAPTERS)}")
    return _crawl(site, limit or C.SCRAPER_MAX_POSTINGS)


def run(sites: str = "all") -> int:
    """Crawl the requested tiers/adapters and update their snapshots (append + dedup + retention prune).
    Network, opt-in. Returns the number of new postings added across all adapters."""
    names = _resolve_sites(sites)
    total_new = 0
    for name in names:
        path = _snapshot_path(name)
        existing = _prune_old(_load(path))
        print(f"[scrape] {name}: {len(existing)} cached; crawling up to {C.SCRAPER_MAX_POSTINGS}…")
        got = _crawl(name, C.SCRAPER_MAX_POSTINGS)
        added = 0
        for i, row in enumerate(got, 1):
            if row["url"] and row["url"] not in existing:
                added += 1
            if row["url"]:
                existing[row["url"]] = row
            if i % _CHUNK == 0:
                _save(path, existing)
        _save(path, existing)
        total_new += added
        print(f"[scrape] {name}: +{added} new (snapshot now {len(existing)}) -> {path}")
    print(f"[scrape] done: {total_new} new postings across {len(names)} adapter(s). "
          f"Run `python run_pipeline.py --add SCRAPER` to ingest them.")
    return total_new


def refresh(sites: str = "all") -> None:
    """Real-time refresh: crawl all sources, re-ingest SCRAPER, then run the enrichment layer (Wikidata
    QIDs + agent/LLM descriptions/links + bilingual labels) over the new entities — as a full build does."""
    run(sites)
    from . import incremental          # lazy import (incremental pulls in the heavy pipeline)
    incremental.add_source(C.SRC_SCRAPER, enrich=True)
