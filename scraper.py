# ─────────────────────────────────────────────
# GOOGLE NEWS — per prospect (no API key needed)
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# PREDICTION MARKETS — Kalshi + Polymarket
# High-probability contracts (>60%) count as STRONG signal
# ─────────────────────────────────────────────

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2/markets"
KALSHI_SERIES = ["KXNFLDRAFTPICK", "KXNFLDRAFT1ST", "KXNFLDRAFT1"]


# ── DraftAxis visit intelligence ──────────────────────────────────────────────
DRAFTAXIS_TEAM_VISITS = {}  # populated by fetch_draftaxis_visits()

def fetch_draftaxis_visits():
    """Fetch all 32 teams' Top-30 and private workout visits from DraftAxis RSC endpoint."""
    import urllib.request, re, json as _json
    global DRAFTAXIS_TEAM_VISITS
    try:
        url = "https://draft-axis.com/dashboards/draft-visits"
        req = urllib.request.Request(url, headers={
            "Accept": "text/x-component",
            "RSC": "1",
            "Next-Router-State-Tree": "%5B%22%22%2C%7B%22children%22%3A%5B%22dashboards%22%2C%7B%22children%22%3A%5B%22draft-visits%22%2C%7B%22children%22%3A%5B%22__PAGE__%22%2C%7B%7D%5D%7D%5D%7D%5D%7D%5D",
            "User-Agent": "Mozilla/5.0 (compatible; NFLDraftBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="replace")

        # Unescape the double-encoded JSON in the RSC stream
        unesc = raw.replace('\\"', '"').replace('\\\\', '\\')

        # Find all team blocks — each "visits" array is preceded by a team identifier
        # Pattern: look for visits arrays and team names in the surrounding context
        team_visits = {}
        nfl_teams = ["49ers","Bears","Bengals","Bills","Broncos","Browns","Buccaneers",
                     "Cardinals","Chargers","Chiefs","Colts","Commanders","Cowboys",
                     "Dolphins","Eagles","Falcons","Giants","Jaguars","Jets","Lions",
                     "Packers","Panthers","Patriots","Raiders","Rams","Ravens","Saints",
                     "Seahawks","Steelers","Texans","Titans","Vikings"]

        # Split on team boundaries — find each team name near a visits array
        pos = 0
        visits_positions = []
        while pos < len(unesc):
            vi = unesc.find('"visits":[{"year":202', pos)
            if vi == -1:
                break
            visits_positions.append(vi)
            pos = vi + 1

        for vi in visits_positions:
            # Look back up to 3000 chars for team name
            lookback = unesc[max(0, vi-3000):vi]
            team_found = None
            for team in nfl_teams:
                if f'"{team}"' in lookback:
                    # Use last occurrence
                    team_found = team
            if not team_found:
                continue

            # Extract visits array
            sub = unesc[vi + len('"visits":'):]
            try:
                # Count brackets to find end of array
                bracket_depth = 0
                end = 0
                for i, ch in enumerate(sub):
                    if ch == '[':
                        bracket_depth += 1
                    elif ch == ']':
                        bracket_depth -= 1
                        if bracket_depth == 0:
                            end = i + 1
                            break
                visits_json = sub[:end]
                visits_list = _json.loads(visits_json)
                # Filter 2026, Top-30 (PRI) and Private Workout (WOR) only
                hard = [
                    {"player": v["player"], "pos": v["pos"], "school": v.get("school",""),
                     "visit_type": "Top 30" if v["type"] == "PRI" else "Private Workout"}
                    for v in visits_list
                    if v.get("year") == 2026 and v.get("type") in ("PRI", "WOR")
                ]
                if hard and team_found not in team_visits:
                    team_visits[team_found] = hard
            except Exception:
                continue

        DRAFTAXIS_TEAM_VISITS = team_visits
        total = sum(len(v) for v in team_visits.values())
        print(f"  DraftAxis: loaded {total} hard-intel visits across {len(team_visits)} teams")
        return team_visits

    except Exception as e:
        print(f"  DraftAxis fetch failed: {e} — using static fallback")
        # Static fallback (last known data)
        DRAFTAXIS_TEAM_VISITS = DRAFTAXIS_STATIC_FALLBACK
        return DRAFTAXIS_STATIC_FALLBACK


# Static fallback in case DraftAxis is unreachable
DRAFTAXIS_STATIC_FALLBACK = {
    "Raiders": [{"player":"Fernando Mendoza","pos":"QB","visit_type":"Top 30"},{"player":"Colton Hood","pos":"CB","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Jets": [{"player":"David Bailey","pos":"EDGE","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Colton Hood","pos":"CB","visit_type":"Top 30"},{"player":"Drew Allar","pos":"QB","visit_type":"Private Workout"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Ty Simpson","pos":"QB","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Sonny Styles","pos":"LB","visit_type":"Top 30"}],
    "Cardinals": [{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"David Bailey","pos":"EDGE","visit_type":"Top 30"},{"player":"Jeremiyah Love","pos":"RB","visit_type":"Top 30"},{"player":"Chris Brazzell II","pos":"WR","visit_type":"Top 30"},{"player":"Drew Allar","pos":"QB","visit_type":"Top 30"}],
    "Titans": [{"player":"Jeremiyah Love","pos":"RB","visit_type":"Top 30"},{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Colton Hood","pos":"CB","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Chris Brazzell II","pos":"WR","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Giants": [{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Sonny Styles","pos":"LB","visit_type":"Top 30"}],
    "Browns": [{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Kenyon Sadiq","pos":"TE","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Jordyn Tyson","pos":"WR","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Ty Simpson","pos":"QB","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"}],
    "Commanders": [{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Saints": [{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Chiefs": [{"player":"Rueben Bain Jr","pos":"EDGE","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Colton Hood","pos":"CB","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"}],
    "Dolphins": [{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"}],
    "Cowboys": [{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"},{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Rams": [{"player":"Carnell Tate","pos":"WR","visit_type":"Top 30"},{"player":"Chris Brazzell II","pos":"WR","visit_type":"Top 30"},{"player":"Ty Simpson","pos":"QB","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Ravens": [{"player":"Mansoor Delane","pos":"CB","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Buccaneers": [{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"}],
    "Lions": [{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"}],
    "Vikings": [{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Panthers": [{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Steelers": [{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Makai Lemon","pos":"WR","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Chargers": [{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"}],
    "Eagles": [{"player":"Keldric Faulk","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"}],
    "Bears": [{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Bills": [{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"}],
    "49ers": [{"player":"Denzel Boston","pos":"WR","visit_type":"Top 30"},{"player":"Chris Brazzell II","pos":"WR","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Texans": [{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"C.J. Allen","pos":"LB","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Patriots": [{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Oscar Delp","pos":"TE","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Seahawks": [{"player":"Cashius Howell","pos":"EDGE","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"}],
    "Bengals": [{"player":"Rueben Bain Jr","pos":"EDGE","visit_type":"Top 30"},{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Kayden McDonald","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Arvell Reese","pos":"EDGE","visit_type":"Top 30"}],
    "Falcons": [{"player":"Emmanuel McNeil-Warren","pos":"S","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Zion Young","pos":"EDGE","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Jaguars": [{"player":"Domani Jackson","pos":"CB","visit_type":"Private Workout"}],
    "Packers": [{"player":"Chris Brazzell II","pos":"WR","visit_type":"Top 30"},{"player":"Malik Muhammad","pos":"CB","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
    "Colts": [{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"},{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"}],
    "Broncos": [{"player":"Christen Miller","pos":"DT","visit_type":"Top 30"},{"player":"Malachi Lawrence","pos":"EDGE","visit_type":"Top 30"}],
}

def fetch_kalshi_signals(results, prospects):
    """
    Pull all Kalshi NFL Draft pick markets via pagination.
    Each market is: Who will be picked Nth in the NFL Draft?
    custom_strike.Person = prospect name, custom_strike.Count = pick number
    yes_ask_dollars = probability (0.0 to 1.0)
    """
    all_markets = []
    for series in KALSHI_SERIES:
        cursor = None
        for _ in range(10):  # max 10 pages per series
            try:
                url = f"{KALSHI_BASE}?series_ticker={series}&limit=100"
                if cursor:
                    url += f"&cursor={cursor}"
                r = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, timeout=10)
                if r.status_code != 200:
                    break
                data = r.json()
                markets = data.get("markets", [])
                all_markets.extend(markets)
                cursor = data.get("cursor")
                if not cursor or not markets:
                    break
                time.sleep(0.3)
            except Exception as e:
                print(f"  Kalshi {series} error: {e}")
                break

    print(f"  Kalshi: {len(all_markets)} markets fetched")

    for market in all_markets:
        try:
            strike = market.get("custom_strike", {})
            person = strike.get("Person", "")
            pick_num = int(strike.get("Count", 0))
            if not person or not pick_num:
                continue

            prob = float(market.get("yes_ask_dollars", 0) or 0)
            if prob < 0.20:
                continue

            # Match prospect name
            matched_prospect = None
            for prospect in prospects:
                parts = [p for p in prospect.lower().split() if len(p) > 3]
                person_lower = person.lower()
                if any(p in person_lower for p in parts):
                    matched_prospect = prospect
                    break
            if not matched_prospect:
                continue

            # Match team by pick number
            matched_team = "GENERAL"
            for team, team_pick in DRAFT_ORDER.items():
                if team_pick == pick_num:
                    matched_team = team
                    break

            # Score
            if prob >= 0.60:
                pts, level = 10, "HIGH"
            elif prob >= 0.40:
                pts, level = 6, "MEDIUM"
            else:
                pts, level = 2, "LOW"

            ticker = market.get("ticker", "")
            link = f"https://kalshi.com/markets/{ticker.lower().split('-')[0]}/{ticker}"
            title = f"[Kalshi {int(prob*100)}%] {person} picked #{pick_num}"

            results[matched_prospect][matched_team]["score"] += pts
            results[matched_prospect][matched_team]["signals"].append(f"Kalshi {int(prob*100)}%")
            results[matched_prospect][matched_team]["signal_levels"].append(level)
            results[matched_prospect][matched_team]["articles"].append({
                "title": title,
                "link": link,
                "source": "Kalshi",
                "published": datetime.now().isoformat(),
            })
        except Exception:
            continue


def fetch_polymarket_signals(results, prospects):
    """Pull Polymarket NFL Draft markets and score high-probability contracts as signal."""
    try:
        r = requests.get(POLYMARKET_API, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            print(f"  Polymarket: HTTP {r.status_code}")
            return
        markets = r.json() if isinstance(r.json(), list) else r.json().get("data", [])
        print(f"  Polymarket: {len(markets)} draft markets found")
        _score_prediction_markets(markets, results, prospects, source="Polymarket",
            title_key="question", yes_price_key="lastTradePrice", ticker_key="id")
    except Exception as e:
        print(f"  Polymarket error: {e}")

def _score_prediction_markets(markets, results, prospects, source, title_key, yes_price_key, ticker_key):
    """
    Score prediction markets using conviction = probability x log(volume).
    High volume + high probability = smart money. Low volume = noise.
    Capped at ONE contribution per prospect-team pair (best conviction wins).
    """
    scored_pairs = set()

    def get_price(m):
        try:
            p = float(m.get(yes_price_key, 0) or 0)
            return p / 100.0 if p > 1 else p
        except:
            return 0

    def get_volume(m):
        try:
            vol = float(m.get("volume_fp", 0) or m.get("volume", 0) or 0)
            return vol / 100.0
        except:
            return 0

    def conviction_score(m):
        return get_price(m) * math.log(get_volume(m) + 1)

    sorted_markets = sorted(markets, key=conviction_score, reverse=True)

    for market in sorted_markets:
        title = str(market.get(title_key, "")).lower()
        if not title:
            continue

        matched_prospect = None
        for prospect in prospects:
            parts = [p for p in prospect.lower().split() if len(p) > 3]
            if any(p in title for p in parts):
                matched_prospect = prospect
                break
        if not matched_prospect:
            continue

        matched_team = "GENERAL"
        for team, aliases in TEAM_ALIASES.items():
            all_terms = [team.lower()] + aliases
            if any(term in title for term in all_terms):
                matched_team = team
                break

        try:
            strike = market.get("custom_strike", {})
            if strike:
                pick_num = int(strike.get("Count", 0))
                if pick_num:
                    for team, team_pick in DRAFT_ORDER.items():
                        if team_pick == pick_num:
                            matched_team = team
                            break
        except:
            pass

        pair_key = matched_prospect + ":" + matched_team
        if pair_key in scored_pairs:
            continue
        scored_pairs.add(pair_key)

        prob = get_price(market)
        vol = get_volume(market)
        if prob < 0.15:
            continue

        # conviction = prob * log(vol) — rewards high volume + high confidence
        conviction = prob * math.log(vol + 1)
        if conviction >= 5.0:    signal_pts, level = 8, "HIGH"
        elif conviction >= 3.0:  signal_pts, level = 6, "HIGH"
        elif conviction >= 1.5:  signal_pts, level = 4, "MEDIUM"
        elif conviction >= 0.5:  signal_pts, level = 2, "LOW"
        else:                    signal_pts, level = 1, "LOW"

        market_title = str(market.get(title_key, ""))
        ticker = str(market.get(ticker_key, ""))
        if source == "Kalshi":
            link = "https://kalshi.com/markets/" + ticker.lower().split("-")[0] + "/" + ticker
        else:
            link = "https://polymarket.com/event/" + ticker
        vol_str = "$" + str(int(vol)) + " vol" if vol > 0 else "low vol"
        label = source + " " + str(int(prob * 100)) + "% (" + vol_str + ")"

        results[matched_prospect][matched_team]["score"] += signal_pts
        results[matched_prospect][matched_team]["signals"].append(label)
        results[matched_prospect][matched_team]["signal_levels"].append(level)
        results[matched_prospect][matched_team]["articles"].append({
            "title": "[" + label + "] " + market_title,
            "link": link,
            "source": source,
            "published": datetime.now().isoformat(),
        })
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

REDDIT_FEEDS = [
    "https://www.reddit.com/r/nfldraft/search.rss?sort=new&limit=25&q={prospect}",
    "https://www.reddit.com/r/nfl/search.rss?sort=new&limit=15&q={prospect}+draft",
]

EXTRA_NEWS_SOURCES = [
    # NFL Draft specialists
    "https://www.draftnetwork.com/feed",
    "https://www.walterfootball.com/rss.xml",
    "https://www.cbssports.com/rss/headlines/nfl/draft/",
    "https://overthecap.com/feed",
    "https://www.pff.com/feed",
    "https://www.profootballnetwork.com/feed/",
    "https://www.si.com/nfl/draft/rss",
    # National NFL coverage
    "https://www.nfl.com/rss/rsslanding?searchString=draft",
    "https://profootballtalk.nbcsports.com/feed/",
    "https://www.theringer.com/rss/nfl/index.xml",
    "https://syndication.bleacherreport.com/streams/teams/feed.xml?team_id=1&sport_id=1",
    "https://sports.yahoo.com/nfl/rss.xml",
    "https://www.sportingnews.com/us/nfl/rss",
    "https://touchdownwire.usatoday.com/feed/",
    "https://www.foxsports.com/rss-feeds?category=nfl",
    "https://www.usatoday.com/sports/nfl/rss",
    "https://athlonsports.com/nfl/feed",
    "https://www.nfltraderumors.co/feed/",
    "https://www.thescore.com/rss/nfl/news",
]

def fetch_reddit(prospect, days_back=7):
    """Fetch Reddit posts mentioning a prospect via RSS."""
    cache_url = f"reddit:{prospect}"
    cached = get_cached(cache_url)
    if cached:
        return cached
    cutoff = datetime.now().astimezone() - timedelta(days=days_back)
    articles = []
    for feed_template in REDDIT_FEEDS:
        url = feed_template.replace("{prospect}", requests.utils.quote(prospect))
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            for entry in feed.entries[:10]:
                pub_raw = entry.get("published", "") or entry.get("updated", "")
                pub_dt = parse_date(pub_raw)
                if pub_dt:
                    if pub_dt.tzinfo is None:
                        pub_dt = pub_dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
                    if pub_dt < cutoff:
                        continue
                text = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text(" ", strip=True)
                articles.append({
                    "title": entry.get("title", ""),
                    "summary": text[:400],
                    "link": entry.get("link", ""),
                    "published": pub_raw,
                    "pub_dt": pub_dt.isoformat() if pub_dt else "",
                    "source": entry.get("link","").split("/")[2].replace("www.",""),
                })
            time.sleep(0.3)
        except Exception:
            continue
    set_cache(cache_url, articles)
    return articles

def fetch_extra_sources(results, prospects, days_back=7):
    """Scrape extra national NFL news sources for prospect mentions."""
    print(f"  Extra sources: scraping {len(EXTRA_NEWS_SOURCES)} feeds...")
    for url in EXTRA_NEWS_SOURCES:
        articles = fetch_feed(url, days_back=days_back)
        time.sleep(0.3)
        for article in articles:
            for prospect in prospects:
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

def fetch_all_google_news(results, prospects):
    """Search Google News + Reddit for each prospect and score results."""
    print(f"  Google News + Reddit: searching {len(prospects)} prospects...")
    for i, prospect in enumerate(prospects):
        print(f"\r  Searching: {i+1}/{len(prospects)} — {prospect}    ", end="", flush=True)
        # Google News
        for article in fetch_google_news(prospect):
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
        # Reddit
        for article in fetch_reddit(prospect):
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
        time.sleep(0.4)
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

import math
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
    "Kayden McDonald":       {"pos": "DT",   "college": "Ohio State",   "consensus_rank": 33},
    "Christen Miller":        {"pos": "DT",   "college": "Georgia",       "consensus_rank": 37},
    "Domonique Orange":       {"pos": "DT",   "college": "Iowa State",    "consensus_rank": 48},
    "Lee Hunter":             {"pos": "DT",   "college": "Texas Tech",    "consensus_rank": 53},
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
    "Derrick Moore": "Derrick Moore",  # specific to avoid confusion
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
    "McDonald": "Kayden McDonald", "Kayden": "Kayden McDonald",
    "Miller": "Christen Miller", "Christen": "Christen Miller",
    "Orange": "Domonique Orange", "Domonique": "Domonique Orange",
    "Hunter": "Lee Hunter", "Lee": "Lee Hunter",
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
# TEAM ALIASES — city names, nicknames, coaches, stadiums
# so "Kansas City" maps to Chiefs, "Foxborough" to Patriots, etc.
# ─────────────────────────────────────────────
TEAM_ALIASES = {
    "Raiders": ["las vegas", "raiders", "silver and black"],
    "Jets": ["new york jets", "jets", "gang green", "metlife"],
    "Cardinals": ["arizona", "cardinals", "state farm stadium"],
    "Titans": ["tennessee", "titans", "nashville", "nissan stadium"],
    "Giants": ["new york giants", "giants", "big blue"],
    "Browns": ["cleveland", "browns", "dawg pound"],
    "Commanders": ["washington", "commanders", "fedex field"],
    "Saints": ["new orleans", "saints", "superdome"],
    "Chiefs": ["kansas city", "chiefs", "arrowhead", "andy reid"],
    "Bengals": ["cincinnati", "bengals", "paycor"],
    "Dolphins": ["miami", "dolphins", "hardrock", "hard rock"],
    "Cowboys": ["dallas", "cowboys", "jerry jones", "at&t stadium"],
    "Rams": ["los angeles rams", "l.a. rams", "sofi stadium"],
    "Ravens": ["baltimore", "ravens", "lamar jackson", "m&t bank"],
    "Buccaneers": ["tampa bay", "buccaneers", "bucs", "raymond james"],
    "Lions": ["detroit", "lions", "ford field"],
    "Vikings": ["minnesota", "vikings", "us bank"],
    "Panthers": ["carolina", "panthers", "bank of america"],
    "Steelers": ["pittsburgh", "steelers", "heinz field", "acrisure"],
    "Chargers": ["los angeles chargers", "l.a. chargers", "chargers", "sofi"],
    "Eagles": ["philadelphia", "eagles", "lincoln financial", "linc"],
    "Bears": ["chicago", "bears", "soldier field"],
    "Bills": ["buffalo", "bills", "highmark"],
    "49ers": ["san francisco", "49ers", "niners", "levi's stadium"],
    "Texans": ["houston", "texans", "nrg stadium"],
    "Patriots": ["new england", "patriots", "foxborough", "gillette"],
    "Seahawks": ["seattle", "seahawks", "lumen field"],
    "Falcons": ["atlanta", "falcons", "mercedes-benz"],
    "Colts": ["indianapolis", "colts", "lucas oil"],
    "Packers": ["green bay", "packers", "lambeau"],
    "Jaguars": ["jacksonville", "jaguars", "everbank"],
    "Broncos": ["denver", "broncos", "empower field"],
}


# ─────────────────────────────────────────────
# 2026 NFL DRAFT ORDER (Round 1)
# ─────────────────────────────────────────────
DRAFT_ORDER = {
    # Confirmed 2026 NFL Draft Round 1 order (per NFL.com, ESPN, NBC Sports)
    "Raiders": 1,
    "Jets": 2,        # Also holds pick 16 (from Colts)
    "Cardinals": 3,
    "Titans": 4,
    "Giants": 5,
    "Browns": 6,
    "Commanders": 7,
    "Saints": 8,
    "Chiefs": 9,
    "Bengals": 10,
    "Dolphins": 11,
    "Cowboys": 12,    # Also holds pick 20 (via trade)
    "Rams": 13,       # From Falcons
    "Ravens": 14,
    "Buccaneers": 15,
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
    "Patriots": 31,
    "Seahawks": 32,   # Super Bowl LX champions
    # Teams with NO Round 1 pick in 2026 (traded away):
    # Falcons (traded to Rams), Colts (traded to Jets),
    # Packers, Jaguars, Broncos (traded for Jaylen Waddle)
}

NO_ROUND1_PICK = {"Falcons", "Colts", "Packers", "Jaguars", "Broncos"}



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

    # Check if this team (or any of its aliases) appears in the text
    if team != "GENERAL":
        team_terms = [team.lower()] + TEAM_ALIASES.get(team, [])
        if not any(term in text for term in team_terms):
            return 0, [], []

    # For GENERAL scoring: only score if NO specific team is mentioned
    # This prevents articles about specific teams from being double-counted as GENERAL
    if team == "GENERAL":
        for other_team, aliases in TEAM_ALIASES.items():
            all_terms = [other_team.lower()] + aliases
            if any(term in text for term in all_terms):
                return 0, [], []  # Skip GENERAL if a team is identifiable

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
        if team != "GENERAL":
            team_terms = [team.lower()] + TEAM_ALIASES.get(team, [])
            t_idx = min((text.find(term) for term in team_terms if text.find(term) != -1), default=-1)
        else:
            t_idx = -1

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
            score += 3
        elif pick_diff <= 8:
            score += 1

    return score, matched_signals[:3], matched_level[:3]

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

    # Google News + Reddit + extra sources
    print("  Searching Google News + Reddit for each prospect...")
    fetch_all_google_news(results, list(TOP_PROSPECTS.keys()))
    print("  Google News + Reddit complete")

    # Extra national NFL sources
    print("  Scraping extra national sources...")
    fetch_extra_sources(results, list(TOP_PROSPECTS.keys()))
    print("  Extra sources complete")

    # Prediction markets
    print("  Fetching Kalshi prediction markets...")
    fetch_kalshi_signals(results, list(TOP_PROSPECTS.keys()))
    print("  Fetching Polymarket prediction markets...")
    fetch_polymarket_signals(results, list(TOP_PROSPECTS.keys()))
    print("  Prediction markets complete")

    # DraftAxis pre-draft visit intelligence
    print("  Fetching DraftAxis pre-draft visit data...")
    fetch_draftaxis_visits()
    print("  DraftAxis complete")

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

        # Build DraftAxis visit data for this prospect
        da_teams = []
        da_visit_count = 0
        for da_team, da_visits in DRAFTAXIS_TEAM_VISITS.items():
            for v in da_visits:
                if v["player"].lower().startswith(prospect.split()[0].lower()) and (
                    len(prospect.split()) < 2 or prospect.split()[-1][:4].lower() in v["player"].lower()
                ):
                    da_teams.append({"team": da_team, "visit_type": v["visit_type"]})
                    da_visit_count += 1
                    break

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
            "draft_axis": {
                "visit_count": da_visit_count,
                "visiting_teams": da_teams,
                "source": "draft-axis.com",
                "visit_type_label": "Top 30 / Private Workout"
            },
        })

    # Sort by total signal activity (most buzz first)
    output["prospects"].sort(key=lambda p: p["total_signal_score"], reverse=True)

    # Generate signal-driven mock draft
    try:
        new_mock = generate_mock_draft(output["prospects"])
        # Load previous mock draft to compute movement
        prev_mock = {}
        prev_path = Path("draft_intel.json")
        if prev_path.exists():
            try:
                prev_data = json.loads(prev_path.read_text())
                for pick in prev_data.get("mock_draft", []):
                    prev_mock[pick["prospect"]] = pick["pick"]
            except Exception:
                pass
        # Annotate each pick with movement vs previous run
        for pick in new_mock:
            prospect = pick["prospect"]
            prev_pick = prev_mock.get(prospect)
            if prev_pick is None:
                pick["movement"] = "NEW"
                pick["prev_pick"] = None
            elif prev_pick == pick["pick"]:
                pick["movement"] = "STABLE"
                pick["prev_pick"] = prev_pick
            elif prev_pick > pick["pick"]:
                pick["movement"] = "UP"
                pick["prev_pick"] = prev_pick
            else:
                pick["movement"] = "DOWN"
                pick["prev_pick"] = prev_pick
        output["mock_draft"] = new_mock
        print(f"  Mock draft: {len(output['mock_draft'])} picks generated")
    except Exception as e:
        print(f"  Mock draft error: {e}")
        output["mock_draft"] = []
    return output


def generate_mock_draft(prospects):
    """
    Composite-scored Round 1 mock draft.
    Each pick scores every available prospect by:
    - Consensus rank match to pick number (exact = +50, 1-off = +20, within 3 = +5)
    - Beat reporter signal score for that specific team
    Highest composite wins. Confidence reflects whether it's a lock, signal-driven, or fallback.
    """
    draft_slots = sorted(DRAFT_ORDER.items(), key=lambda x: x[1])
    used = set()
    mock = []

    for team, pick_num in draft_slots:
        available = [p for p in prospects if p["name"] not in used]
        if not available:
            continue

        best = None
        best_meta = {}
        best_composite = -999

        for p in available:
            td = next((t for t in (p.get("teams") or []) if t["team"] == team), None)
            signal = td["score"] if td else 0
            rank = p.get("consensus_rank") or 999
            diff = abs(rank - pick_num)

            composite = signal
            if diff == 0:    composite += 50
            elif diff == 1:  composite += 20
            elif diff <= 3:  composite += 5
            elif diff > 10:  composite -= 10

            if composite > best_composite:
                best_composite = composite
                best = p
                best_meta = {"td": td, "signal": signal, "rank": rank, "diff": diff}

        if not best:
            continue

        used.add(best["name"])
        td = best_meta["td"]
        signal = best_meta["signal"]
        diff = best_meta["diff"]

        if diff == 0 and signal >= 10:   confidence, note = "HIGH", "Consensus lock + signal"
        elif diff == 0:                   confidence, note = "HIGH", "Consensus lock"
        elif signal >= 15 and diff <= 5: confidence, note = "HIGH", "Strong signal"
        elif diff == 1:                   confidence, note = "HIGH", "Consensus fit"
        elif signal >= 8:                 confidence, note = "MEDIUM", "Signal-driven"
        elif diff <= 5:                   confidence, note = "MEDIUM", "Consensus range"
        else:                             confidence, note = "LOW", "Best available"

        mock.append({
            "pick": pick_num,
            "team": team,
            "prospect": best["name"],
            "pos": best.get("pos", ""),
            "college": best.get("college", ""),
            "consensus_rank": best.get("consensus_rank"),
            "signal_score": signal,
            "top_signals": (td or {}).get("top_signals", [])[:2],
            "top_article_title": (td or {}).get("top_articles", [{}])[0].get("title", "") if (td or {}).get("top_articles") else "",
            "top_article_link": (td or {}).get("top_articles", [{}])[0].get("link", "") if (td or {}).get("top_articles") else "",
            "top_article_source": (td or {}).get("top_articles", [{}])[0].get("source", "") if (td or {}).get("top_articles") else "",
            "confidence": confidence,
            "note": note,
        })

    return mock


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
