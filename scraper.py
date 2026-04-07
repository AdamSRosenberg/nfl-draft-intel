# ─────────────────────────────────────────────
# GOOGLE NEWS — per prospect (no API key needed)
# ─────────────────────────────────────────────

GOOGLE_NEWS_BASE = "https://news.google.com/rss/search?hl=en-US&gl=US&ceid=US:en&q="

def fetch_google_news(prospect_name, days_back=7):
    """Search Google News RSS for a prospect and return recent articles."""
    cache_url = f"gnews:{prospect_name}"
    cached = get_cached(cache_url)
    if cached:
        return cached

    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    query = requests.utils.quote(f'"{prospect_name}" NFL draft 2026')
    url = GOOGLE_NEWS_BASE + query
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        articles = []
        for entry in feed.entries[:20]:
            pub_raw = entry.get("published", "") or entry.get("updated", "")
            pub_dt = parse_date(pub_raw)
            if pub_dt:
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                if pub_dt < cutoff:
                    continue
            text = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)
            source = entry.get("source", {}).get("title", "") or entry.get("link", "").split("/")[2].replace("www.", "")
            articles.append({
                "title": entry.get("title", ""),
                "summary": text[:400],
                "link": entry.get("link", ""),
                "published": pub_raw,
                "pub_dt": pub_dt.isoformat() if pub_dt else "",
                "source": source,
            })
            if len(articles) >= 15:
                break
        set_cache(cache_url, articles)
        return articles
    except Exception:
        return []

def fetch_all_google_news(results, prospects):
    """Search Google News for each prospect and score results against all teams."""
    print(f"  Google News: searching {len(prospects)} prospects...")
    for i, prospect in enumerate(prospects):
        print(f"\r  Google News: {i+1}/{len(prospects)} — {prospect}    ", end="", flush=True)
        articles = fetch_google_news(prospect)
        time.sleep(0.5)  # be polite
        for article in articles:
            for team in list(FEEDS.keys()) + ["GENERAL"]:
                score, signals, levels = score_article(article, prospect, team)
                if score > 0:
                    results[prospect][team]["score"] += score
                    results[prospect][team]["signals"].extend(signals)
                    results[prospect][team]["signal_levels"].extend(levels)
                    results[prospect][team]["articles"].append({
                        "title": article["title"],
                        "link": article["link"],
                        "source": article["source"],
                        "published": article["pub_dt"] or article["published"],
                    })
    print()

#!/usr/bin/env python3
"""
NFL Draft Intelligence Aggregator v3 — 2026 CLASS
===================================================
Scrapes beat reporter RSS feeds and outputs JSON
for the AI-powered dashboard.

Usage:
    python3 nfl_draft_intel_v3.py              # Run, print JSON to terminal
    python3 nfl_draft_intel_v3.py --save       # Save to draft_intel.json
    python3 nfl_draft_intel_v3.py --pretty     # Pretty-print JSON
    python3 nfl_draft_intel_v3.py --refresh    # Force refresh cache
    python3 nfl_draft_intel_v3.py --demo       # Demo mode (no internet)
"""

import feedparser
import requests
import json
import re
import time
import argparse
import hashlib
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

CACHE_DIR = Path("/tmp/nfl_draft_cache_v3")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_TTL_MINUTES = 60

# ─────────────────────────────────────────────
#  VERIFIED 2026 NFL DRAFT PROSPECTS
# ─────────────────────────────────────────────
TOP_PROSPECTS = {
    "Fernando Mendoza":       {"pos": "QB",   "college": "Indiana",       "consensus_rank": 1},
    "Arvell Reese":           {"pos": "EDGE", "college": "Ohio State",    "consensus_rank": 2},
    "Jeremiyah Love":         {"pos": "RB",   "college": "Notre Dame",    "consensus_rank": 3},
    "Sonny Styles":           {"pos": "LB",   "college": "Ohio State",    "consensus_rank": 4},
    "Caleb Downs":            {"pos": "S",    "college": "Ohio State",    "consensus_rank": 5},
    "Francis Mauigoa":        {"pos": "OT",   "college": "Miami",         "consensus_rank": 6},
    "David Bailey":           {"pos": "EDGE", "college": "Texas Tech",    "consensus_rank": 7},
    "Rueben Bain Jr":         {"pos": "EDGE", "college": "Miami",         "consensus_rank": 8},
    "Carnell Tate":           {"pos": "WR",   "college": "Ohio State",    "consensus_rank": 9},
    "Makai Lemon":            {"pos": "WR",   "college": "USC",           "consensus_rank": 10},
    "Kenyon Sadiq":           {"pos": "TE",   "college": "Oregon",        "consensus_rank": 11},
    "Jordyn Tyson":           {"pos": "WR",   "college": "Arizona State", "consensus_rank": 12},
    "Mansoor Delane":         {"pos": "CB",   "college": "LSU",           "consensus_rank": 13},
    "Spencer Fano":           {"pos": "OT",   "college": "Utah",          "consensus_rank": 14},
    "Monroe Freeling":        {"pos": "OT",   "college": "Georgia",       "consensus_rank": 15},
    "Ty Simpson":             {"pos": "QB",   "college": "Alabama",       "consensus_rank": 16},
    "Olaivavega Ioane":       {"pos": "OG",   "college": "Penn State",    "consensus_rank": 17},
    "Jermod McCoy":           {"pos": "CB",   "college": "Tennessee",     "consensus_rank": 18},
    "Kadyn Proctor":          {"pos": "OT",   "college": "Alabama",       "consensus_rank": 19},
    "Avieon Terrell":         {"pos": "CB",   "college": "Clemson",       "consensus_rank": 20},
    "Dillon Thieneman":       {"pos": "S",    "college": "Oregon",        "consensus_rank": 21},
    "Peter Woods":            {"pos": "DL",   "college": "Clemson",       "consensus_rank": 22},
    "Denzel Boston":          {"pos": "WR",   "college": "Washington",    "consensus_rank": 23},
    "Akheem Mesidor":         {"pos": "EDGE", "college": "Miami",         "consensus_rank": 24},
    "Omar Cooper Jr":         {"pos": "WR",   "college": "Indiana",       "consensus_rank": 25},
    "T.J. Parker":            {"pos": "EDGE", "college": "Clemson",       "consensus_rank": 26},
    "Anthony Hill Jr":        {"pos": "LB",   "college": "Texas",         "consensus_rank": 27},
    "Keldric Faulk":          {"pos": "EDGE", "college": "Auburn",        "consensus_rank": 28},
    "Emmanuel McNeil-Warren": {"pos": "S",    "college": "Toledo",        "consensus_rank": 29},
    "C.J. Allen":             {"pos": "LB",   "college": "Georgia",       "consensus_rank": 30},
    "Harold Perkins Jr":      {"pos": "LB",   "college": "LSU",           "consensus_rank": 31},
    "Caleb Lomu":             {"pos": "OT",   "college": "Utah",          "consensus_rank": 32},
    # 33-50 — verified from Scouts Inc., Daniel Jeremiah, Walter Football
    "Zion Young":             {"pos": "EDGE", "college": "Missouri",      "consensus_rank": 33},
    "Cashius Howell":         {"pos": "EDGE", "college": "Texas A&M",     "consensus_rank": 34},
    "Chase Bisontis":         {"pos": "OG",   "college": "Texas A&M",     "consensus_rank": 35},
    "Caleb Banks":            {"pos": "DT",   "college": "Florida",       "consensus_rank": 36},
    "Eli Stowers":            {"pos": "TE",   "college": "Vanderbilt",    "consensus_rank": 37},
    "Brandon Cisse":          {"pos": "CB",   "college": "South Carolina","consensus_rank": 38},
    "Zachariah Branch":       {"pos": "WR",   "college": "Georgia",       "consensus_rank": 39},
    "Max Iheanachor":         {"pos": "OT",   "college": "Arizona State", "consensus_rank": 40},
    "Chris Brazzell II":      {"pos": "WR",   "college": "Tennessee",     "consensus_rank": 41},
    "Germie Bernard":         {"pos": "WR",   "college": "Alabama",       "consensus_rank": 42},
    "Gabe Jacas":             {"pos": "EDGE", "college": "Illinois",      "consensus_rank": 43},
    "Jacob Rodriguez":        {"pos": "LB",   "college": "Texas Tech",    "consensus_rank": 44},
    "Emmanuel Pregnon":       {"pos": "OG",   "college": "Oregon",        "consensus_rank": 45},
    "Colton Hood":            {"pos": "CB",   "college": "Tennessee",     "consensus_rank": 46},
    "Darrell Jackson Jr":     {"pos": "DT",   "college": "Florida State", "consensus_rank": 47},
    "Domani Jackson":         {"pos": "CB",   "college": "Alabama",       "consensus_rank": 48},
    "Carson Beck":            {"pos": "QB",   "college": "Miami",         "consensus_rank": 49},
    "Drew Allar":             {"pos": "QB",   "college": "Penn State",    "consensus_rank": 50},
    # 51-75 — verified from Scouts Inc., Mel Kiper, Bleacher Report, NFL.com
    "Garrett Nussmeier":      {"pos": "QB",   "college": "LSU",           "consensus_rank": 51},
    "Derrick Moore":          {"pos": "EDGE", "college": "Michigan",      "consensus_rank": 52},
    "R Mason Thomas":         {"pos": "EDGE", "college": "Oklahoma",      "consensus_rank": 53},
    "Jaishawn Barham":        {"pos": "LB",   "college": "Michigan",      "consensus_rank": 54},
    "Romello Height":         {"pos": "EDGE", "college": "Texas Tech",    "consensus_rank": 55},
    "Keyron Crawford":        {"pos": "EDGE", "college": "Auburn",        "consensus_rank": 56},
    "Sam Hecht":              {"pos": "C",    "college": "Kansas State",  "consensus_rank": 57},
    "Jake Slaughter":         {"pos": "C",    "college": "Florida",       "consensus_rank": 58},
    "Kyle Louis":             {"pos": "LB",   "college": "Pittsburgh",    "consensus_rank": 59},
    "Ja'Kobi Lane":           {"pos": "WR",   "college": "USC",           "consensus_rank": 60},
    "Malachi Fields":         {"pos": "WR",   "college": "Notre Dame",    "consensus_rank": 61},
    "De'Zhaun Stribling":     {"pos": "WR",   "college": "Ole Miss",      "consensus_rank": 62},
    "Mike Washington Jr":     {"pos": "RB",   "college": "Arkansas",      "consensus_rank": 63},
    "Jadarian Price":         {"pos": "RB",   "college": "Notre Dame",    "consensus_rank": 64},
    "Zakee Wheatley":         {"pos": "S",    "college": "Penn State",    "consensus_rank": 65},
    "A.J. Haulcy":            {"pos": "S",    "college": "LSU",           "consensus_rank": 66},
    "Jalon Kilgore":          {"pos": "S",    "college": "South Carolina","consensus_rank": 67},
    "Davison Igbinosun":      {"pos": "CB",   "college": "Ohio State",    "consensus_rank": 68},
    "Malik Muhammad":         {"pos": "CB",   "college": "Texas",         "consensus_rank": 69},
    "Caleb Tiernan":          {"pos": "OT",   "college": "Northwestern",  "consensus_rank": 70},
    "Dametrious Crownover":   {"pos": "OT",   "college": "Texas A&M",     "consensus_rank": 71},
    "Oscar Delp":             {"pos": "TE",   "college": "Georgia",       "consensus_rank": 72},
    "Max Klare":              {"pos": "TE",   "college": "Ohio State",    "consensus_rank": 73},
    "Deion Burks":            {"pos": "WR",   "college": "Oklahoma",      "consensus_rank": 74},
    "Elijah Sarratt":         {"pos": "WR",   "college": "Indiana",       "consensus_rank": 75},
}

PROSPECT_ALIASES = {
    "Mendoza": "Fernando Mendoza", "Fernando": "Fernando Mendoza",
    "Reese": "Arvell Reese", "Arvell": "Arvell Reese",
    "Love": "Jeremiyah Love", "Jeremiyah": "Jeremiyah Love",
    "Styles": "Sonny Styles", "Sonny": "Sonny Styles",
    "Downs": "Caleb Downs",
    "Mauigoa": "Francis Mauigoa", "Francis": "Francis Mauigoa",
    "Bailey": "David Bailey",
    "Bain": "Rueben Bain Jr", "Rueben": "Rueben Bain Jr",
    "Tate": "Carnell Tate", "Carnell": "Carnell Tate",
    "Lemon": "Makai Lemon", "Makai": "Makai Lemon",
    "Sadiq": "Kenyon Sadiq", "Kenyon": "Kenyon Sadiq",
    "Tyson": "Jordyn Tyson", "Jordyn": "Jordyn Tyson",
    "Delane": "Mansoor Delane", "Mansoor": "Mansoor Delane",
    "Fano": "Spencer Fano", "Spencer": "Spencer Fano",
    "Freeling": "Monroe Freeling", "Monroe": "Monroe Freeling",
    "Simpson": "Ty Simpson",
    "Ioane": "Olaivavega Ioane", "Vega": "Olaivavega Ioane",
    "McCoy": "Jermod McCoy", "Jermod": "Jermod McCoy",
    "Proctor": "Kadyn Proctor", "Kadyn": "Kadyn Proctor",
    "Terrell": "Avieon Terrell", "Avieon": "Avieon Terrell",
    "Thieneman": "Dillon Thieneman",
    "Woods": "Peter Woods",
    "Boston": "Denzel Boston",
    "Mesidor": "Akheem Mesidor",
    "Cooper": "Omar Cooper Jr",
    "Parker": "T.J. Parker",
    "Hill": "Anthony Hill Jr",
    "Faulk": "Keldric Faulk",
    "McNeil": "Emmanuel McNeil-Warren",
    "Allen": "C.J. Allen",
    "Perkins": "Harold Perkins Jr",
    "Lomu": "Caleb Lomu",
    "Young": "Zion Young",
    "Zion": "Zion Young",
    "Howell": "Cashius Howell",
    "Bisontis": "Chase Bisontis",
    "Banks": "Caleb Banks",
    "Stowers": "Eli Stowers",
    "Cisse": "Brandon Cisse",
    "Branch": "Zachariah Branch",
    "Iheanachor": "Max Iheanachor",
    "Brazzell": "Chris Brazzell II",
    "Bernard": "Germie Bernard",
    "Jacas": "Gabe Jacas",
    "Rodriguez": "Jacob Rodriguez",
    "Pregnon": "Emmanuel Pregnon",
    "Hood": "Colton Hood",
    "Beck": "Carson Beck",
    "Allar": "Drew Allar",
    "Nussmeier": "Garrett Nussmeier",
    "Garrett": "Garrett Nussmeier",
    "Moore": "Derrick Moore",
    "Thomas": "R Mason Thomas",
    "Barham": "Jaishawn Barham",
    "Height": "Romello Height",
    "Crawford": "Keyron Crawford",
    "Hecht": "Sam Hecht",
    "Slaughter": "Jake Slaughter",
    "Louis": "Kyle Louis",
    "Lane": "Ja'Kobi Lane",
    "Fields": "Malachi Fields",
    "Stribling": "De'Zhaun Stribling",
    "Washington": "Mike Washington Jr",
    "Price": "Jadarian Price",
    "Jadarian": "Jadarian Price",
    "Wheatley": "Zakee Wheatley",
    "Haulcy": "A.J. Haulcy",
    "Kilgore": "Jalon Kilgore",
    "Igbinosun": "Davison Igbinosun",
    "Muhammad": "Malik Muhammad",
    "Tiernan": "Caleb Tiernan",
    "Crownover": "Dametrious Crownover",
    "Delp": "Oscar Delp",
    "Klare": "Max Klare",
    "Burks": "Deion Burks",
    "Sarratt": "Elijah Sarratt",
}

CONNECTION_SIGNALS = {
    "HIGH": [
        "top-30 visit", "top 30 visit", "official visit", "pre-draft visit",
        "visited", "workout", "worked out", "met with", "meeting with",
        "targets", "targeting", "wants", "number one pick", "first pick",
        "trade up", "trading up", "will take", "plans to take",
        "priority", "prioritizing", "fallen for", "in love with",
    ],
    "MEDIUM": [
        "interested in", "interest in", "considering", "looking at",
        "on the radar", "could take", "might take", "may take",
        "fit", "perfect fit", "ideal fit", "makes sense", "need at",
        "linked to", "connected to", "mock", "projected to",
        "expected to go", "rumored", "buzz", "chatter", "hearing",
        "sources say", "sources indicate", "league sources", "per sources",
    ],
    "LOW": [
        "scout", "scouted", "watched", "impressive", "could be",
        "option", "possibility", "speculation", "reported",
    ],
}
WEIGHTS = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

# ─────────────────────────────────────────────
# 2026 NFL DRAFT ORDER (Round 1)
# ─────────────────────────────────────────────
DRAFT_ORDER = {
    "Raiders": 1,
    "Jets": 2,
    "Cardinals": 3,
    "Patriots": 4,
    "Giants": 5,
    "Browns": 6,
    "Commanders": 7,
    "Saints": 8,
    "Titans": 9,
    "Bengals": 10,
    "Dolphins": 11,
    "Cowboys": 12,
    "Rams": 13,
    "Ravens": 14,
    "Buccaneers": 15,
    "Falcons": 16,
    "Lions": 17,
    "Vikings": 18,
    "Panthers": 19,
    "Steelers": 21,
    "Chargers": 22,
    "Eagles": 23,
    "Bears": 25,
    "Bills": 26,
    "49ers": 27,
    "Texans": 28,
    "Colts": 29,
    "Jaguars": 30,
    "Packers": 31,
    "Seahawks": 32,
    # Teams without a Round 1 pick (traded away):
    # Chiefs, Broncos, Colts picks may be via trade
}



FEEDS = {
    "Raiders":    ["https://www.silverandblackpride.com/rss/current.xml", "https://www.reviewjournal.com/sports/raiders-nfl/feed/"],
    "Browns":     ["https://www.dawgpounddaily.com/rss/current.xml", "https://www.cleveland.com/browns/rss"],
    "Giants":     ["https://www.bigblueview.com/rss/current.xml", "https://www.nj.com/giants/rss"],
    "Patriots":   ["https://www.patspulpit.com/rss/current.xml", "https://www.masslive.com/patriots/rss"],
    "Jaguars":    ["https://www.bigcatcountry.com/rss/current.xml", "https://www.jacksonville.com/sports/jaguars/rss"],
    "Jets":       ["https://www.gangreengangblog.com/rss/current.xml", "https://www.nj.com/jets/rss"],
    "Panthers":   ["https://www.catechism.net/rss/current.xml", "https://www.charlotteobserver.com/sports/nfl/carolina-panthers/rss"],
    "Saints":     ["https://www.canalstreetchronicles.com/rss/current.xml", "https://www.nola.com/sports/saints/rss"],
    "Titans":     ["https://www.musiccitymiracles.com/rss/current.xml", "https://www.tennessean.com/sports/titans/rss"],
    "Bears":      ["https://www.windycitygridiron.com/rss/current.xml", "https://www.chicagotribune.com/sports/bears/rss"],
    "Falcons":    ["https://www.thefalcoholic.com/rss/current.xml", "https://www.ajc.com/sports/falcons/rss"],
    "Commanders": ["https://www.hogshaven.com/rss/current.xml", "https://www.washingtonpost.com/sports/nfl/rss"],
    "Dolphins":   ["https://www.thephinsider.com/rss/current.xml", "https://www.miamiherald.com/sports/nfl/miami-dolphins/rss"],
    "Colts":      ["https://www.stampedeblueblog.com/rss/current.xml", "https://www.indystar.com/sports/colts/rss"],
    "Seahawks":   ["https://www.fieldgulls.com/rss/current.xml", "https://www.seattletimes.com/sports/seahawks/feed/"],
    "Broncos":    ["https://www.milehighreport.com/rss/current.xml", "https://www.denverpost.com/sports/denver-broncos/feed/"],
    "Cardinals":  ["https://www.revenge-of-the-birds.com/rss/current.xml", "https://www.azcentral.com/sports/nfl/cardinals/rss"],
    "Bengals":    ["https://www.cincyjungle.com/rss/current.xml", "https://www.cincinnati.com/sports/bengals/rss"],
    "Steelers":   ["https://www.behindthesteelcurtain.com/rss/current.xml", "https://www.post-gazette.com/sports/steelers/rss"],
    "Cowboys":    ["https://www.bloggingtheboys.com/rss/current.xml", "https://www.dallasnews.com/sports/cowboys/rss"],
    "Bills":      ["https://www.buffalorumblings.com/rss/current.xml"],
    "Ravens":     ["https://www.baltimoresun.com/sports/ravens/rss"],
    "Texans":     ["https://www.battleredblog.com/rss/current.xml"],
    "Chiefs":     ["https://www.arrowheadpride.com/rss/current.xml"],
    "Chargers":   ["https://www.boltsfromtheblue.com/rss/current.xml"],
    "Packers":    ["https://www.acmepackingcompany.com/rss/current.xml"],
    "Vikings":    ["https://www.dailynorseman.com/rss/current.xml"],
    "Lions":      ["https://www.prideofdetroit.com/rss/current.xml"],
    "Buccaneers": ["https://www.bucsnationnfl.com/rss/current.xml"],
    "49ers":      ["https://www.ninersnation.com/rss/current.xml"],
    "Rams":       ["https://www.theramsden.com/rss/current.xml"],
    "Eagles":     ["https://www.bleeding-green-nation.com/rss/current.xml"],
    "GENERAL": [
        "https://www.cbssports.com/rss/headlines/nfl/draft/",
        "https://www.pff.com/feed",
        "https://overthecap.com/feed",
        "https://www.walterfootball.com/rss.xml",
        "https://www.draftnetwork.com/feed",
        "https://www.si.com/nfl/draft/rss",
    ],
}

# ─────────────────────────────────────────────
#  CACHE
# ─────────────────────────────────────────────
def cache_key(url):
    return CACHE_DIR / hashlib.md5(url.encode()).hexdigest()

def get_cached(url):
    p = cache_key(url)
    if p.exists():
        if datetime.now() - datetime.fromtimestamp(p.stat().st_mtime) < timedelta(minutes=CACHE_TTL_MINUTES):
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
    return None

def set_cache(url, data):
    try:
        cache_key(url).write_text(json.dumps(data, default=str))
    except Exception:
        pass

# ─────────────────────────────────────────────
#  FETCH
# ─────────────────────────────────────────────
def parse_date(s):
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    for fmt in ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s.strip(), fmt)
        except Exception:
            pass
    return None

def fetch_feed(url, days_back=90):
    cached = get_cached(url)
    if cached:
        return cached
    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        articles = []
        for entry in feed.entries[:20]:
            pub_raw = entry.get("published", "") or entry.get("updated", "")
            pub_dt = parse_date(pub_raw)
            if pub_dt:
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                if pub_dt < cutoff:
                    continue
            text = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)
            articles.append({
                "title":     entry.get("title", ""),
                "summary":   text[:400],
                "link":      entry.get("link", ""),
                "published": pub_raw,
                "pub_dt":    pub_dt.isoformat() if pub_dt else "",
                "source":    url.split("/")[2].replace("www.", ""),
            })
            if len(articles) >= 15:
                break
        set_cache(url, articles)
        return articles
    except Exception:
        return []

# ─────────────────────────────────────────────
#  TWITTER/X BEAT REPORTERS (via Nitter RSS)
#  No API key needed — uses public Nitter mirrors
# ─────────────────────────────────────────────
BEAT_REPORTERS = {
    # National NFL/Draft reporters
    "TomPelissero":     "GENERAL",
    "RapSheet":         "GENERAL",
    "MikeGarafolo":     "GENERAL",
    "CharlesRobinson":  "GENERAL",
    "AlbertBreer":      "GENERAL",
    "PFF_Sam":          "GENERAL",
    "mike_florio":      "GENERAL",
    "DanGrazianoESPN":  "GENERAL",
    "mortreport":       "GENERAL",
    "AdamSchefter":     "GENERAL",
    # Team beat reporters
    "MikeReiss":        "Patriots",
    "ZackCox33":        "Patriots",
    "MaryKayCabot":     "Browns",
    "PaulKuharskyNFL":  "Titans",
    "BradBiggs":        "Bears",
    "PatrickFinley":    "Bears",
    "RalphVacchiano":   "Giants",
    "jordanraanan":     "Giants",
    "mattschneidman":   "Packers",
    "RobDemovsky":      "Packers",
    "gregauman":        "Buccaneers",
    "Clarence_Hill_Jr": "Cowboys",
    "nicki_jhabvala":   "Commanders",
    "John_Keim":        "Commanders",
    "BobMcManaman":     "Cardinals",
    "chrismccloskey":   "Colts",
    "StaceyDales":      "GENERAL",
    "ian693":           "GENERAL",
    "diannaESPN":       "GENERAL",
}

NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
    "https://nitter.kavin.rocks",
]

def get_nitter_instance():
    """Find a working Nitter instance."""
    for instance in NITTER_INSTANCES:
        try:
            r = requests.get(f"{instance}/twitter", timeout=5,
                           headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                return instance
        except Exception:
            continue
    return None

def fetch_twitter(handle, team, nitter_base, days_back=3):
    """Scrape tweets from a beat reporter via Nitter RSS."""
    cache_url = f"nitter:{handle}"
    cached = get_cached(cache_url)
    if cached:
        return cached

    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    rss_url = f"{nitter_base}/{handle}/rss"

    try:
        r = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if r.status_code != 200:
            return []
        feed = feedparser.parse(r.content)
        tweets = []
        for entry in feed.entries[:20]:
            pub_raw = entry.get("published", "")
            pub_dt = parse_date(pub_raw)
            if pub_dt:
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                if pub_dt < cutoff:
                    continue
            text = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)
            title = entry.get("title", "")
            tweets.append({
                "title":     title[:200],
                "summary":   text[:400],
                "link":      entry.get("link", "").replace(nitter_base, "https://twitter.com"),
                "published": pub_raw,
                "pub_dt":    pub_dt.isoformat() if pub_dt else "",
                "source":    f"@{handle} (Twitter)",
            })
            if len(tweets) >= 10:
                break
        set_cache(cache_url, tweets)
        return tweets
    except Exception:
        return []

def fetch_all_twitter(results, prospects):
    """Fetch tweets from all beat reporters and score them."""
    nitter = get_nitter_instance()
    if not nitter:
        print("  No Nitter instance available — skipping Twitter scrape")
        return

    print(f"  Twitter: using {nitter}")
    for handle, team in BEAT_REPORTERS.items():
        tweets = fetch_twitter(handle, team, nitter)
        time.sleep(0.3)
        for tweet in tweets:
            for prospect in prospects:
                score, signals, levels = score_article(tweet, prospect, team)
                if score > 0:
                    results[prospect][team]["score"] += score
                    results[prospect][team]["signals"].extend(signals)
                    results[prospect][team]["signal_levels"].extend(levels)
                    results[prospect][team]["articles"].append({
                        "title":     tweet["title"],
                        "link":      tweet["link"],
                        "source":    tweet["source"],
                        "published": tweet["pub_dt"] or tweet["published"],
                    })

# ─────────────────────────────────────────────
#  SCORE
# ─────────────────────────────────────────────
def resolve_prospect(name):
    if name in TOP_PROSPECTS:
        return name
    for alias, full in PROSPECT_ALIASES.items():
        if alias.lower() == name.lower():
            return full
    for full in TOP_PROSPECTS:
        if name.lower() in full.lower():
            return full
    return name

def score_article(article, prospect, team):
    text = f"{article['title']} {article['summary']}".lower()
    parts = [p for p in prospect.lower().split() if len(p) > 3]
    if not any(p in text for p in parts):
        return 0, [], []
    if team.lower() not in text and team != "GENERAL":
        return 0, [], []
    score = 0
    matched_signals = []
    matched_level = []
    for level, keywords in CONNECTION_SIGNALS.items():
        for kw in keywords:
            if kw in text:
                score += WEIGHTS[level]
                matched_signals.append(kw)
                matched_level.append(level)
    if score > 0:
        p_idx = next((text.find(p) for p in parts if text.find(p) != -1), -1)
        t_idx = text.find(team.lower())
        if p_idx != -1 and t_idx != -1:
            dist = abs(p_idx - t_idx)
            if dist < 100:
                score += 2
            elif dist < 300:
                score += 1
        # Boost score if team's pick slot is close to prospect's consensus rank
        prospect_rank = TOP_PROSPECTS.get(prospect, {}).get("consensus_rank", 999)
        team_pick = DRAFT_ORDER.get(team, 999)
        pick_diff = abs(prospect_rank - team_pick)
        if pick_diff <= 3:
            score += 3  # Very likely range
        elif pick_diff <= 8:
            score += 1  # Plausible range
    return score, matched_signals[:3], matched_level[:3]

# ─────────────────────────────────────────────
#  AGGREGATE → JSON
# ─────────────────────────────────────────────
def aggregate(refresh=False):
    if refresh:
        for f in CACHE_DIR.glob("*"):
            f.unlink()

    results = defaultdict(lambda: defaultdict(lambda: {
        "score": 0, "signals": [], "signal_levels": [], "articles": []
    }))

    total_feeds = sum(len(v) for v in FEEDS.values())
    fetched = 0

    for team, urls in FEEDS.items():
        for url in urls:
            fetched += 1
            print(f"\r  Fetching feeds... {fetched}/{total_feeds}", end="", flush=True)
            articles = fetch_feed(url)
            time.sleep(0.05)
            for article in articles:
                for prospect in TOP_PROSPECTS:
                    score, signals, levels = score_article(article, prospect, team)
                    if score > 0:
                        results[prospect][team]["score"] += score
                        results[prospect][team]["signals"].extend(signals)
                        results[prospect][team]["signal_levels"].extend(levels)
                        results[prospect][team]["articles"].append({
                            "title":     article["title"],
                            "link":      article["link"],
                            "source":    article["source"],
                            "published": article["pub_dt"] or article["published"],
                        })

    print()

    # Twitter/X beat reporters
    print("  Scraping Twitter/X beat reporters via Nitter...")
    fetch_all_twitter(results, list(TOP_PROSPECTS.keys()))
    print("  Twitter scrape complete")

    # Build structured output
    output = {
        "generated_at": datetime.now().isoformat(),
        "draft_date": "2026-04-23",
        "prospects": []
    }

    for prospect, info in TOP_PROSPECTS.items():
        team_data = results.get(prospect, {})
        sorted_teams = sorted(
            [(t, d) for t, d in team_data.items() if d["score"] > 0],
            key=lambda x: x[1]["score"], reverse=True
        )

        # Dedupe signals
        teams_out = []
        for team, data in sorted_teams[:8]:
            seen = set()
            unique_sigs = []
            unique_lvls = []
            for s, l in zip(data["signals"], data["signal_levels"]):
                if s not in seen:
                    seen.add(s)
                    unique_sigs.append(s)
                    unique_lvls.append(l)
            teams_out.append({
                "team": team,
                "score": data["score"],
                "top_signals": unique_sigs[:4],
                "signal_levels": unique_lvls[:4],
                "article_count": len(data["articles"]),
                "top_articles": data["articles"][:3],
            })

        total_score = sum(d["score"] for _, d in sorted_teams)
        top_team = sorted_teams[0][0] if sorted_teams else None

        output["prospects"].append({
            "name": prospect,
            "pos": info["pos"],
            "college": info["college"],
            "consensus_rank": info["consensus_rank"],
            "total_signal_score": total_score,
            "top_landing_spot": top_team,
            "teams": teams_out,
            "has_twitter_signal": any(
                "@" in a.get("source","")
                for t in teams_out
                for a in t.get("top_articles",[])
            ),
        })

    # Sort by total signal activity (most buzz first)
    output["prospects"].sort(key=lambda p: p["total_signal_score"], reverse=True)

    return output

# ─────────────────────────────────────────────
#  DEMO DATA
# ─────────────────────────────────────────────
DEMO_OUTPUT = {
    "generated_at": datetime.now().isoformat(),
    "draft_date": "2026-04-23",
    "_note": "DEMO MODE — paste real output from live run into dashboard for AI analysis",
    "prospects": [
        {"name": "Fernando Mendoza", "pos": "QB", "college": "Indiana", "consensus_rank": 1, "total_signal_score": 42,
         "top_landing_spot": "Raiders",
         "teams": [{"team": "Raiders", "score": 38, "top_signals": ["top-30 visit", "targeting", "priority", "per sources"], "signal_levels": ["HIGH","HIGH","HIGH","MEDIUM"], "article_count": 4, "top_articles": [{"title": "Raiders brass locks in Mendoza as franchise QB target", "link": "https://silverandblackpride.com", "source": "silverandblackpride.com", "published": "2026-04-05T10:00:00"}]}, {"team": "Browns", "score": 18, "top_signals": ["considering", "sources say"], "signal_levels": ["MEDIUM","MEDIUM"], "article_count": 2, "top_articles": [{"title": "Browns keeping options open at #2 if Raiders surprise", "link": "https://dawgpounddaily.com", "source": "dawgpounddaily.com", "published": "2026-04-04T09:00:00"}]}]},
        {"name": "Arvell Reese", "pos": "EDGE", "college": "Ohio State", "consensus_rank": 2, "total_signal_score": 35,
         "top_landing_spot": "Browns",
         "teams": [{"team": "Browns", "score": 30, "top_signals": ["pre-draft visit", "targeting", "buzz"], "signal_levels": ["HIGH","HIGH","MEDIUM"], "article_count": 3, "top_articles": [{"title": "Browns host Reese — EDGE rush top priority at #2", "link": "https://dawgpounddaily.com", "source": "dawgpounddaily.com", "published": "2026-04-06T08:00:00"}]}, {"team": "Giants", "score": 18, "top_signals": ["interested in", "fit"], "signal_levels": ["MEDIUM","MEDIUM"], "article_count": 2, "top_articles": [{"title": "Giants could pivot to Reese if Love gone", "link": "https://bigblueview.com", "source": "bigblueview.com", "published": "2026-04-04T11:00:00"}]}]},
        {"name": "Carnell Tate", "pos": "WR", "college": "Ohio State", "consensus_rank": 9, "total_signal_score": 28,
         "top_landing_spot": "Titans",
         "teams": [{"team": "Titans", "score": 26, "top_signals": ["visit", "targeting", "perfect fit", "sources say"], "signal_levels": ["HIGH","HIGH","HIGH","MEDIUM"], "article_count": 3, "top_articles": [{"title": "Titans beat: Tate visited Nashville, Tennessee targeting WR1", "link": "https://musiccitymiracles.com", "source": "musiccitymiracles.com", "published": "2026-04-05T12:00:00"}]}, {"team": "Bears", "score": 12, "top_signals": ["interested in"], "signal_levels": ["MEDIUM"], "article_count": 1, "top_articles": [{"title": "Bears monitor WR situation ahead of draft", "link": "https://windycitygridiron.com", "source": "windycitygridiron.com", "published": "2026-04-03T14:00:00"}]}]},
        {"name": "David Bailey", "pos": "EDGE", "college": "Texas Tech", "consensus_rank": 7, "total_signal_score": 24,
         "top_landing_spot": "Saints",
         "teams": [{"team": "Saints", "score": 22, "top_signals": ["top-30 visit", "interested in", "buzz"], "signal_levels": ["HIGH","MEDIUM","MEDIUM"], "article_count": 2, "top_articles": [{"title": "Saints eye Bailey — New Orleans desperate for pass rush upgrade", "link": "https://canalstreetchronicles.com", "source": "canalstreetchronicles.com", "published": "2026-04-06T09:00:00"}]}, {"team": "Titans", "score": 14, "top_signals": ["considering"], "signal_levels": ["MEDIUM"], "article_count": 1, "top_articles": [{"title": "Titans weigh EDGE options heading into final draft week", "link": "https://musiccitymiracles.com", "source": "musiccitymiracles.com", "published": "2026-04-04T10:00:00"}]}]},
        {"name": "Jeremiyah Love", "pos": "RB", "college": "Notre Dame", "consensus_rank": 3, "total_signal_score": 22,
         "top_landing_spot": "Giants",
         "teams": [{"team": "Giants", "score": 20, "top_signals": ["visit", "priority", "linked to"], "signal_levels": ["HIGH","HIGH","MEDIUM"], "article_count": 2, "top_articles": [{"title": "Giants host Love — NY targeting offensive weapon at #3", "link": "https://bigblueview.com", "source": "bigblueview.com", "published": "2026-04-05T13:00:00"}]}, {"team": "Broncos", "score": 10, "top_signals": ["considering"], "signal_levels": ["MEDIUM"], "article_count": 1, "top_articles": [{"title": "Broncos could trade up for Love if board falls right", "link": "https://milehighreport.com", "source": "milehighreport.com", "published": "2026-04-03T10:00:00"}]}]},
        {"name": "Rueben Bain Jr", "pos": "EDGE", "college": "Miami", "consensus_rank": 8, "total_signal_score": 18,
         "top_landing_spot": "Jets",
         "teams": [{"team": "Jets", "score": 16, "top_signals": ["visit", "buzz", "sources say"], "signal_levels": ["HIGH","MEDIUM","MEDIUM"], "article_count": 2, "top_articles": [{"title": "Jets visit Bain — arm length concerns not a dealbreaker per sources", "link": "https://gangreengangblog.com", "source": "gangreengangblog.com", "published": "2026-04-04T11:00:00"}]}, {"team": "Panthers", "score": 10, "top_signals": ["interested in"], "signal_levels": ["MEDIUM"], "article_count": 1, "top_articles": [{"title": "Panthers evaluating Bain as EDGE option at #7", "link": "https://catechism.net", "source": "catechism.net", "published": "2026-04-03T09:00:00"}]}]},
    ]
}

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", "-s", action="store_true", default=True, help="Save to draft_intel.json")
    parser.add_argument("--pretty",  "-p", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--refresh", "-r", action="store_true", help="Force refresh cache")
    parser.add_argument("--demo",    "-d", action="store_true", help="Demo mode")
    args = parser.parse_args()

    if args.demo:
        data = DEMO_OUTPUT
    else:
        print("NFL Draft Intel v3 — 2026 Class")
        print(f"Scraping {sum(len(v) for v in FEEDS.values())} feeds across 33 teams...\n")
        data = aggregate(refresh=args.refresh)

    indent = 2 if args.pretty else None
    output = json.dumps(data, indent=indent, default=str)

    if args.save:
        out_path = Path("draft_intel.json")
        out_path.write_text(output)
        print(f"Saved to {out_path.absolute()}")
        print(f"Prospects with signal: {sum(1 for p in data['prospects'] if p['total_signal_score'] > 0)}")
        print(f"Generated: {data['generated_at']}")
        print(f"\nPaste the contents of draft_intel.json into the dashboard for AI analysis.")
    else:
        print(output)

if __name__ == "__main__":
    main()
