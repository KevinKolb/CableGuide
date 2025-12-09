#!/usr/bin/env python3
"""
Fetch real TV listings and update guide.xml.

- Only adds new channels or updates existing channels
- Never deletes channels (use archiver.py for that)
- Preserves channels not in the current update
"""

import os
import re
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import xml.dom.minidom

import requests
from bs4 import BeautifulSoup


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_soup(url: str, headers: dict | None = None, timeout: int = 15) -> BeautifulSoup:
    """Fetch a URL and return BeautifulSoup, raising on HTTP error.

    Keeps all network logic in one place so individual channel functions stay tidy.
    """
    hdrs = headers or DEFAULT_HEADERS
    resp = requests.get(url, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.content, "html.parser")


def get_current_time_slots() -> list[str]:
    """Generate 8 half-hour time slots starting from the current hour."""
    now = datetime.now()
    current = now.replace(minute=0, second=0, microsecond=0)

    slots: list[str] = []
    for i in range(8):
        t = current + timedelta(minutes=i * 30)
        slots.append(t.strftime("%I:%M %p").lstrip("0"))
    return slots


# ------------------------------------------------------------
# Channel scrapers + fallbacks
# ------------------------------------------------------------

def get_cnn_schedule() -> list[dict]:
    """Fetch CNN schedule from cnn.com/tv/schedule, with fallback."""
    print("🔍 Fetching CNN schedule from CNN.com...")
    try:
        soup = fetch_soup("https://www.cnn.com/tv/schedule")

        schedule: list[dict] = []

        # CNN uses a bunch of templates; be generous with selectors.
        possible_selectors = [
            {"class_": re.compile(r"schedule|program|show|listing", re.I)},
            {"attrs": {"data-test": re.compile(r"schedule|program", re.I)}},
            {"class_": re.compile(r"card.*schedule", re.I)},
        ]

        items = []
        for sel in possible_selectors:
            if "attrs" in sel:
                found = soup.find_all(["div", "article", "li", "tr"], sel["attrs"])
            else:
                found = soup.find_all(["div", "article", "li", "tr"], class_=sel["class_"])
            if found:
                items = found
                break

        # Light JSON-LD sniff (doesn't change logic, just future-proofs)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict) and "itemListElement" in data:
                    # You could parse structured data here later if needed.
                    pass
            except Exception:
                continue

        for item in items[:12]:
            # Time
            time_elem = item.find(
                ["span", "div", "time"],
                class_=re.compile(r"time|hour", re.I),
            ) or item.find(
                ["span", "div"],
                string=re.compile(r"\d{1,2}:\d{2}\s*[AP]M", re.I),
            )

            # Title
            title_elem = item.find(
                ["h2", "h3", "h4", "span", "a"],
                class_=re.compile(r"title|name|headline", re.I),
            ) or item.find(["h2", "h3", "h4", "a"])

            # Description
            desc_elem = item.find(
                ["p", "div", "span"],
                class_=re.compile(r"desc|summary|detail|content", re.I),
            )

            if not (time_elem and title_elem):
                continue

            time_text = time_elem.get_text(strip=True)
            title_text = title_elem.get_text(strip=True)
            description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

            m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_text, re.I)
            if not m:
                continue

            hours, mins, period = m.group(1), m.group(2), m.group(3).upper()
            schedule.append(
                {
                    "start": f"{hours}:{mins} {period}",
                    "duration": 60,
                    "title": title_text[:100],
                    "description": description,
                }
            )

        # Dedup (by start + title)
        unique: list[dict] = []
        seen: set[tuple] = set()
        for show in schedule:
            key = (show["start"], show["title"])
            if key not in seen:
                seen.add(key)
                unique.append(show)

        if unique:
            print(f"✅ Found {len(unique)} CNN shows from CNN.com")
            return unique[:8]

        print("⚠️  Could not parse CNN schedule from website; using fallback.")
        return get_cnn_fallback_schedule()

    except Exception as e:
        print(f"⚠️  Error fetching CNN schedule: {e}")
        print("📺 Using fallback CNN schedule")
        return get_cnn_fallback_schedule()


def get_cnn_fallback_schedule() -> list[dict]:
    """Fallback CNN schedule based on typical programming."""
    now = datetime.now()
    current_hour = now.hour

    if 0 <= current_hour < 4:
        schedule = [
            {
                "start": "12:00 AM",
                "duration": 60,
                "title": "CNN Tonight",
                "description": "Late night news coverage and analysis.",
            },
            {
                "start": "1:00 AM",
                "duration": 60,
                "title": "CNN Newsroom",
                "description": "Breaking news and top stories from around the world.",
            },
            {
                "start": "2:00 AM",
                "duration": 60,
                "title": "CNN Newsroom",
                "description": "Breaking news and top stories from around the world.",
            },
            {
                "start": "3:00 AM",
                "duration": 60,
                "title": "Early Start",
                "description": "Early morning news to start your day.",
            },
        ]
    elif 4 <= current_hour < 9:
        schedule = [
            {
                "start": "4:00 AM",
                "duration": 120,
                "title": "Early Start",
                "description": "Early morning news to start your day.",
            },
            {
                "start": "6:00 AM",
                "duration": 180,
                "title": "CNN News Central",
                "description": "Morning news with the latest headlines.",
            },
        ]
    elif 9 <= current_hour < 13:
        schedule = [
            {
                "start": "9:00 AM",
                "duration": 60,
                "title": "CNN News Central",
                "description": "Morning news with the latest headlines.",
            },
            {
                "start": "10:00 AM",
                "duration": 60,
                "title": "CNN Newsroom",
                "description": "Breaking news and top stories from around the world.",
            },
            {
                "start": "11:00 AM",
                "duration": 60,
                "title": "Inside Politics",
                "description": "Political news and analysis with John King.",
            },
            {
                "start": "12:00 PM",
                "duration": 60,
                "title": "Inside Politics",
                "description": "Political news and analysis with John King.",
            },
        ]
    elif 13 <= current_hour < 16:
        schedule = [
            {
                "start": "1:00 PM",
                "duration": 60,
                "title": "CNN Newsroom",
                "description": "Breaking news and top stories from around the world.",
            },
            {
                "start": "2:00 PM",
                "duration": 60,
                "title": "CNN Newsroom",
                "description": "Breaking news and top stories from around the world.",
            },
            {
                "start": "3:00 PM",
                "duration": 60,
                "title": "The Lead with Jake Tapper",
                "description": "Afternoon news with Jake Tapper.",
            },
        ]
    elif 16 <= current_hour < 20:
        schedule = [
            {
                "start": "4:00 PM",
                "duration": 60,
                "title": "The Lead with Jake Tapper",
                "description": "Afternoon news with Jake Tapper.",
            },
            {
                "start": "5:00 PM",
                "duration": 60,
                "title": "The Situation Room",
                "description": "Evening news with Wolf Blitzer.",
            },
            {
                "start": "6:00 PM",
                "duration": 60,
                "title": "The Situation Room",
                "description": "Evening news with Wolf Blitzer.",
            },
            {
                "start": "7:00 PM",
                "duration": 60,
                "title": "Erin Burnett OutFront",
                "description": "Prime time news with Erin Burnett.",
            },
        ]
    else:  # 20-24
        schedule = [
            {
                "start": "8:00 PM",
                "duration": 60,
                "title": "Anderson Cooper 360",
                "description": "Prime time news and interviews with Anderson Cooper.",
            },
            {
                "start": "9:00 PM",
                "duration": 60,
                "title": "Anderson Cooper 360",
                "description": "Prime time news and interviews with Anderson Cooper.",
            },
            {
                "start": "10:00 PM",
                "duration": 60,
                "title": "CNN Tonight",
                "description": "Late night news coverage and analysis.",
            },
            {
                "start": "11:00 PM",
                "duration": 60,
                "title": "CNN Tonight",
                "description": "Late night news coverage and analysis.",
            },
        ]

    return schedule


def get_espn_schedule() -> list[dict]:
    """Fetch ESPN schedule, with fallback."""
    print("🔍 Fetching ESPN schedule from ESPN.com...")
    try:
        soup = fetch_soup("https://www.espn.com/watch/schedule")

        schedule: list[dict] = []
        items = soup.find_all(["div", "article"], class_=re.compile(r"schedule|event|game", re.I))

        for item in items[:8]:
            time_elem = item.find(
                ["span", "time"], string=re.compile(r"\d{1,2}:\d{2}", re.I)
            )
            title_elem = item.find(
                ["h3", "h4", "span"], class_=re.compile(r"title|name", re.I)
            )
            desc_elem = item.find(
                ["p", "span"], class_=re.compile(r"desc|detail", re.I)
            )

            if not (time_elem and title_elem):
                continue

            time_text = time_elem.get_text(strip=True)
            m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", time_text, re.I)
            if not m:
                continue

            hours, mins, period = m.group(1), m.group(2), (m.group(3) or "PM").upper()

            schedule.append(
                {
                    "start": f"{hours}:{mins} {period}",
                    "duration": 120,
                    "title": title_elem.get_text(strip=True)[:100],
                    "description": (
                        desc_elem.get_text(strip=True)[:200]
                        if desc_elem
                        else "Live sports coverage."
                    ),
                }
            )

        if schedule:
            print(f"✅ Found {len(schedule)} ESPN shows")
            return schedule[:8]

    except Exception as e:
        print(f"⚠️  Error fetching ESPN: {e}")

    print("📺 Using fallback ESPN schedule")
    return [
        {
            "start": "12:00 PM",
            "duration": 30,
            "title": "SportsCenter",
            "description": "Your home for sports news, highlights, and analysis.",
        },
        {
            "start": "12:30 PM",
            "duration": 30,
            "title": "NFL Live",
            "description": "NFL news, analysis, and insider information.",
        },
        {
            "start": "1:00 PM",
            "duration": 60,
            "title": "NBA Today",
            "description": "Breaking NBA news and game previews.",
        },
        {
            "start": "2:00 PM",
            "duration": 120,
            "title": "College Football",
            "description": "Live college football coverage.",
        },
    ]


def get_fox_schedule() -> list[dict]:
    """Fetch FOX schedule, with fallback."""
    print("🔍 Fetching FOX schedule from FOX.com...")
    try:
        soup = fetch_soup("https://www.fox.com/schedule/")

        schedule: list[dict] = []
        items = soup.find_all(
            ["div", "article", "li"], class_=re.compile(r"schedule|show|program", re.I)
        )

        for item in items[:8]:
            time_elem = item.find(
                ["span", "time"], string=re.compile(r"\d{1,2}:\d{2}", re.I)
            )
            title_elem = item.find(["h2", "h3", "h4"])

            if not (time_elem and title_elem):
                continue

            time_text = time_elem.get_text(strip=True)
            m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_text, re.I)
            if not m:
                continue

            schedule.append(
                {
                    "start": f"{m.group(1)}:{m.group(2)} {m.group(3).upper()}",
                    "duration": 30,
                    "title": title_elem.get_text(strip=True)[:100],
                    "description": "FOX primetime entertainment.",
                }
            )

        if schedule:
            print(f"✅ Found {len(schedule)} FOX shows")
            return schedule[:8]

    except Exception as e:
        print(f"⚠️  Error fetching FOX: {e}")

    print("📺 Using fallback FOX schedule")
    return [
        {
            "start": "12:00 PM",
            "duration": 30,
            "title": "The Simpsons",
            "description": "Animated sitcom about the Simpson family.",
        },
        {
            "start": "12:30 PM",
            "duration": 30,
            "title": "Bob's Burgers",
            "description": "Animated comedy about a family-run restaurant.",
        },
        {
            "start": "1:00 PM",
            "duration": 60,
            "title": "NFL on FOX",
            "description": "NFL football coverage and analysis.",
        },
        {
            "start": "2:00 PM",
            "duration": 120,
            "title": "FOX Sports",
            "description": "Sports coverage and highlights.",
        },
    ]


def get_nbc_schedule() -> list[dict]:
    """Fetch NBC schedule, with fallback."""
    print("🔍 Fetching NBC schedule from NBC.com...")
    try:
        soup = fetch_soup("https://www.nbc.com/schedule")

        schedule: list[dict] = []
        items = soup.find_all(["div", "article"], class_=re.compile(r"schedule|show", re.I))

        for item in items[:8]:
            time_elem = item.find(["span", "time"])
            title_elem = item.find(["h2", "h3", "h4"])

            if not (time_elem and title_elem):
                continue

            time_text = time_elem.get_text(strip=True)
            m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_text, re.I)
            if not m:
                continue

            schedule.append(
                {
                    "start": f"{m.group(1)}:{m.group(2)} {m.group(3).upper()}",
                    "duration": 60,
                    "title": title_elem.get_text(strip=True)[:100],
                    "description": "NBC programming.",
                }
            )

        if schedule:
            print(f"✅ Found {len(schedule)} NBC shows")
            return schedule[:8]

    except Exception as e:
        print(f"⚠️  Error fetching NBC: {e}")

    print("📺 Using fallback NBC schedule")
    return [
        {
            "start": "12:00 PM",
            "duration": 60,
            "title": "Days of Our Lives",
            "description": "Long-running daytime soap opera.",
        },
        {
            "start": "1:00 PM",
            "duration": 60,
            "title": "NBC News Daily",
            "description": "Midday news and current events.",
        },
        {
            "start": "2:00 PM",
            "duration": 60,
            "title": "NBC Nightly News",
            "description": "Evening news with Lester Holt.",
        },
        {
            "start": "3:00 PM",
            "duration": 60,
            "title": "The Kelly Clarkson Show",
            "description": "Talk show with Kelly Clarkson.",
        },
    ]


def get_pbs_schedule() -> list[dict]:
    """Fetch PBS schedule, with fallback."""
    print("🔍 Fetching PBS schedule from PBS.org...")
    try:
        soup = fetch_soup("https://www.pbs.org/schedules/")

        schedule: list[dict] = []
        items = soup.find_all(
            ["div", "article", "li"], class_=re.compile(r"schedule|program|show|listing", re.I)
        )

        for item in items[:8]:
            time_elem = item.find(
                ["span", "time"], string=re.compile(r"\d{1,2}:\d{2}", re.I)
            ) or item.find(
                ["span", "time"], class_=re.compile(r"time|hour", re.I)
            )

            title_elem = item.find(
                ["h2", "h3", "h4", "a"], class_=re.compile(r"title|name|headline", re.I)
            ) or item.find(["h2", "h3", "h4", "a"])

            desc_elem = item.find(
                ["p", "div", "span"], class_=re.compile(r"desc|summary|detail", re.I)
            )

            if not (time_elem and title_elem):
                continue

            time_text = time_elem.get_text(strip=True)
            m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", time_text, re.I)
            if not m:
                continue

            hours, mins, period = m.group(1), m.group(2), (m.group(3) or "PM").upper()

            schedule.append(
                {
                    "start": f"{hours}:{mins} {period}",
                    "duration": 60,
                    "title": title_elem.get_text(strip=True)[:100],
                    "description": (
                        desc_elem.get_text(strip=True)[:200]
                        if desc_elem
                        else "PBS educational programming."
                    ),
                }
            )

        if schedule:
            print(f"✅ Found {len(schedule)} PBS shows")
            return schedule[:8]

    except Exception as e:
        print(f"⚠️  Error fetching PBS: {e}")

    print("📺 Using fallback PBS schedule")
    return [
        {
            "start": "12:00 PM",
            "duration": 60,
            "title": "PBS NewsHour",
            "description": "In-depth news coverage and analysis.",
        },
        {
            "start": "1:00 PM",
            "duration": 60,
            "title": "Masterpiece",
            "description": "British dramas and period pieces.",
        },
        {
            "start": "2:00 PM",
            "duration": 60,
            "title": "NOVA",
            "description": "Science documentaries exploring the natural world.",
        },
        {
            "start": "3:00 PM",
            "duration": 60,
            "title": "Antiques Roadshow",
            "description": "Appraisals of antiques and collectibles.",
        },
    ]


# ------------------------------------------------------------
# Channel metadata (type and source)
# ------------------------------------------------------------

CHANNEL_METADATA = {
    "CNN": {"type": "broadcast", "source": "CNN"},
    "ESPN": {"type": "broadcast", "source": "ESPN"},
    "FOX": {"type": "broadcast", "source": "FOX"},
    "NBC": {"type": "broadcast", "source": "NBC"},
    "PBS": {"type": "broadcast", "source": "PBS"},
    "ABC": {"type": "broadcast", "source": "ABC"},
    "NFLX1": {"type": "streaming", "source": "Netflix"},
    "HBO1": {"type": "streaming", "source": "HBO Max"},
    "HULU1": {"type": "streaming", "source": "Hulu"},
    "ATV+": {"type": "streaming", "source": "Apple TV+"},
    "P+": {"type": "streaming", "source": "Paramount+"},
    "PCOK": {"type": "streaming", "source": "Peacock"},
}


# ------------------------------------------------------------
# Channel catalog (live + static/streaming)
# ------------------------------------------------------------

def get_channel_schedules() -> dict:
    """Return dict of all channels and their schedules."""
    return {
        "CNN": {
            "name": "CNN",
            "schedule": get_cnn_schedule(),
        },
        "ESPN": {
            "name": "ESPN",
            "schedule": get_espn_schedule(),
        },
        "FOX": {
            "name": "FOX",
            "schedule": get_fox_schedule(),
        },
        "NBC": {
            "name": "NBC",
            "schedule": get_nbc_schedule(),
        },
        "PBS": {
            "name": "PBS",
            "schedule": get_pbs_schedule(),
        },
        "NFLX1": {
            "name": "Netflix 1",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "Stranger Things",
                    "description": "Sci-fi horror series set in 1980s Indiana.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 60,
                    "title": "The Crown",
                    "description": "Drama chronicling the reign of Queen Elizabeth II.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 120,
                    "title": "Movie: Glass Onion",
                    "description": "A detective investigates a murder mystery on a private island.",
                },
            ],
        },
        "HBO1": {
            "name": "HBO 1",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "House of the Dragon",
                    "description": "Prequel to Game of Thrones set 200 years earlier.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 30,
                    "title": "Last Week Tonight",
                    "description": "Satirical news and current events with John Oliver.",
                },
                {
                    "start": "1:30 PM",
                    "duration": 30,
                    "title": "Real Time with Bill Maher",
                    "description": "Political talk show with Bill Maher.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 120,
                    "title": "Movie: Dune Part Two",
                    "description": "Epic sci-fi sequel following Paul Atreides' journey.",
                },
            ],
        },
        "HULU1": {
            "name": "Hulu 1",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "The Handmaid's Tale",
                    "description": "Dystopian drama based on Margaret Atwood's novel.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 30,
                    "title": "Only Murders in the Building",
                    "description": "Mystery comedy about true crime podcasters.",
                },
                {
                    "start": "1:30 PM",
                    "duration": 30,
                    "title": "The Bear",
                    "description": "Drama about a chef running a Chicago sandwich shop.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 90,
                    "title": "Movie: Poor Things",
                    "description": "Fantasy comedy about a young woman brought back to life.",
                },
            ],
        },
        "ATV+": {
            "name": "Apple TV+",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "Ted Lasso",
                    "description": "Comedy about an American football coach in England.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 60,
                    "title": "Severance",
                    "description": "Sci-fi thriller about work-life separation technology.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 120,
                    "title": "Movie: Killers of the Flower Moon",
                    "description": "Crime drama about the Osage Nation murders.",
                },
            ],
        },
        "P+": {
            "name": "Paramount+",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "Yellowstone",
                    "description": "Western drama about the Dutton family ranch.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 30,
                    "title": "Star Trek: Strange New Worlds",
                    "description": "Sci-fi series exploring new worlds and civilizations.",
                },
                {
                    "start": "1:30 PM",
                    "duration": 30,
                    "title": "The Good Fight",
                    "description": "Legal drama spin-off of The Good Wife.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 120,
                    "title": "Movie: Top Gun: Maverick",
                    "description": "Action sequel following Pete 'Maverick' Mitchell.",
                },
            ],
        },
        "PCOK": {
            "name": "Peacock",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 30,
                    "title": "The Office (Rerun)",
                    "description": "Mockumentary sitcom about office workers.",
                },
                {
                    "start": "12:30 PM",
                    "duration": 30,
                    "title": "Parks and Recreation",
                    "description": "Comedy about a small-town parks department.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 60,
                    "title": "Poker Face",
                    "description": "Mystery series about a woman who can detect lies.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 90,
                    "title": "Movie: Oppenheimer",
                    "description": "Biographical thriller about J. Robert Oppenheimer.",
                },
            ],
        },
        "ABC": {
            "name": "ABC Network",
            "schedule": [
                {
                    "start": "12:00 PM",
                    "duration": 60,
                    "title": "General Hospital",
                    "description": "Long-running medical drama and soap opera.",
                },
                {
                    "start": "1:00 PM",
                    "duration": 60,
                    "title": "GMA3: What You Need to Know",
                    "description": "Afternoon news and lifestyle show.",
                },
                {
                    "start": "2:00 PM",
                    "duration": 60,
                    "title": "ABC News Live",
                    "description": "Breaking news and current events.",
                },
                {
                    "start": "3:00 PM",
                    "duration": 60,
                    "title": "Jeopardy!",
                    "description": "Classic game show with trivia questions.",
                },
            ],
        },
    }


# ------------------------------------------------------------
# Existing guide loader
# ------------------------------------------------------------

def load_existing_channels() -> dict:
    """Load existing channels from guide.xml, if present."""
    if not os.path.exists("guide.xml"):
        return {}

    try:
        tree = ET.parse("guide.xml")
        root = tree.getroot()
        existing: dict = {}

        for channel in root.findall(".//channel"):
            channel_num_el = channel.find("number")
            channel_name_el = channel.find("name")
            shows_elem = channel.find("shows")

            if channel_num_el is None or channel_name_el is None or shows_elem is None:
                continue

            channel_num = channel_num_el.text or ""
            channel_name = channel_name_el.text or ""

            # Load type and source attributes if they exist
            channel_type = channel.get("type", "")
            channel_source = channel.get("source", "")

            schedule: list[dict] = []
            for show in shows_elem.findall("show"):
                schedule.append(
                    {
                        "start": show.get("start", ""),
                        "duration": int(show.get("duration", "30")),
                        "title": show.text or "",
                        "description": show.get("description", ""),
                    }
                )

            if channel_num:
                existing[channel_num] = {
                    "name": channel_name,
                    "schedule": schedule,
                    "type": channel_type,
                    "source": channel_source,
                }

        return existing

    except Exception as e:
        print(f"⚠️  Could not load existing guide.xml: {e}")
        return {}


# ------------------------------------------------------------
# XML writer (with single-quoted description attributes)
# ------------------------------------------------------------

def update_guide_xml() -> None:
    """Update guide.xml with new/updated channels, preserving existing ones."""

    # Load existing
    existing_channels = load_existing_channels()
    print(f"📂 Loaded {len(existing_channels)} existing channels from guide.xml")

    # Fetch new data
    new_channel_data = get_channel_schedules()

    # Merge (new overwrites existing for same channel number)
    merged_channels = existing_channels.copy()
    added: list[str] = []
    updated: list[str] = []

    for channel_num, channel_info in new_channel_data.items():
        if channel_num in merged_channels:
            updated.append(channel_num)
        else:
            added.append(channel_num)
        merged_channels[channel_num] = channel_info

    # Build XML tree
    root = ET.Element("guide")

    # Date
    date_elem = ET.SubElement(root, "date")
    date_elem.text = datetime.now().strftime("%m/%d/%y")

    # Ad
    ad = ET.SubElement(root, "ad")
    ad_text = ET.SubElement(ad, "text")
    ad_text.text = "Call 1-800-CABLE-TV for Premium Channels!"

    # Time slots
    timeslots = ET.SubElement(root, "timeslots")
    for slot in get_current_time_slots():
        t_elem = ET.SubElement(timeslots, "time")
        t_elem.text = slot

    # Channels
    channels_elem = ET.SubElement(root, "channels")

    for channel_num, channel_info in merged_channels.items():
        channel_el = ET.SubElement(channels_elem, "channel")

        # Set type and source attributes
        # First check if they're in the channel_info (from existing XML)
        # Otherwise, look them up in CHANNEL_METADATA
        channel_type = channel_info.get("type") or CHANNEL_METADATA.get(channel_num, {}).get("type", "")
        channel_source = channel_info.get("source") or CHANNEL_METADATA.get(channel_num, {}).get("source", "")

        if channel_type:
            channel_el.set("type", channel_type)
        if channel_source:
            channel_el.set("source", channel_source)

        number_el = ET.SubElement(channel_el, "number")
        number_el.text = channel_num

        name_el = ET.SubElement(channel_el, "name")
        name_el.text = channel_info["name"]

        shows_el = ET.SubElement(channel_el, "shows")

        for show in channel_info["schedule"]:
            show_el = ET.SubElement(shows_el, "show")
            show_el.set("start", show["start"])
            show_el.set("duration", str(show["duration"]))

            desc = show.get("description", "")
            if desc:
                # Escape single quotes so we can safely wrap in single quotes later
                desc_escaped = desc.replace("'", "&apos;")
                show_el.set("description", desc_escaped)

            show_el.text = show["title"]

    # Pretty-print XML
    xml_str = ET.tostring(root, encoding="unicode")
    dom = xml.dom.minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ")

    # Remove blank lines
    lines = [line for line in pretty_xml.split("\n") if line.strip()]
    pretty_xml = "\n".join(lines)

    # Force description attributes to use single quotes:
    # description="...value..."  ->  description='...value...'
    pretty_xml = re.sub(r'description="([^"]*)"', r"description='\1'", pretty_xml)

    # Write file
    with open("guide.xml", "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    # Logging
    print("\n✅ guide.xml updated successfully!")
    print(f"📺 Total channels: {len(merged_channels)}")
    if added:
        print(f"➕ Added: {', '.join(added)}")
    if updated:
        print(f"🔄 Updated: {', '.join(updated)}")
    print(f"🕐 Time slots: {', '.join(get_current_time_slots()[:4])}...")


if __name__ == "__main__":
    update_guide_xml()
