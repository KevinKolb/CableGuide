#!/usr/bin/env python3
"""
Fetch real TV listings and update guide.xml
- Only adds new channels or updates existing channels
- Never deletes channels (use archiver.py for that)
- Preserves channels not in the current update
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import xml.dom.minidom
import os
from bs4 import BeautifulSoup
import re

def get_current_time_slots():
    """Generate time slots starting from current hour"""
    now = datetime.now()
    current_hour = now.replace(minute=0, second=0, microsecond=0)

    slots = []
    for i in range(8):  # 8 time slots (4 hours worth of half-hour slots)
        time = current_hour + timedelta(minutes=i*30)
        slots.append(time.strftime("%I:%M %p").lstrip('0'))

    return slots

def get_cnn_schedule():
    """Fetch real CNN schedule from CNN.com"""
    try:
        print("🔍 Fetching CNN schedule from CNN.com...")

        # CNN.com schedule page
        url = "https://www.cnn.com/tv/schedule"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        schedule = []

        print("📄 Parsing CNN schedule...")

        # CNN uses various formats, look for schedule-related elements
        # Try multiple selectors
        possible_selectors = [
            {'class': re.compile(r'schedule|program|show|listing', re.I)},
            {'data-test': re.compile(r'schedule|program', re.I)},
            {'class': re.compile(r'card.*schedule', re.I)},
        ]

        for selector in possible_selectors:
            items = soup.find_all(['div', 'article', 'li', 'tr'], selector)
            if items:
                print(f"  Found {len(items)} potential schedule items")
                break

        # Also try to find JSON data in script tags
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict) and 'itemListElement' in data:
                    print("  Found structured data")
            except:
                pass

        # Parse found items
        for item in items[:12]:  # Get up to 12 shows
            # Look for time
            time_elem = item.find(['span', 'div', 'time'], class_=re.compile(r'time|hour', re.I))
            if not time_elem:
                time_elem = item.find(['span', 'div'], string=re.compile(r'\d{1,2}:\d{2}\s*[AP]M', re.I))

            # Look for title
            title_elem = item.find(['h2', 'h3', 'h4', 'span', 'a'], class_=re.compile(r'title|name|headline', re.I))
            if not title_elem:
                title_elem = item.find(['h2', 'h3', 'h4', 'a'])

            # Look for description
            desc_elem = item.find(['p', 'div', 'span'], class_=re.compile(r'desc|summary|detail|content', re.I))
            description = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

            if time_elem and title_elem:
                time_text = time_elem.get_text(strip=True)
                title_text = title_elem.get_text(strip=True)

                # Parse time
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_text, re.I)
                if time_match:
                    hours = time_match.group(1)
                    mins = time_match.group(2)
                    period = time_match.group(3).upper()

                    schedule.append({
                        'start': f"{hours}:{mins} {period}",
                        'duration': 60,  # Default to 60 minutes
                        'title': title_text[:100],  # Limit title length
                        'description': description
                    })

        # Remove duplicates
        seen = set()
        unique_schedule = []
        for show in schedule:
            key = (show['start'], show['title'])
            if key not in seen:
                seen.add(key)
                unique_schedule.append(show)

        if unique_schedule:
            print(f"✅ Found {len(unique_schedule)} CNN shows from CNN.com")
            return unique_schedule[:8]  # Return max 8 shows
        else:
            print("⚠️  Could not parse CNN schedule from website")
            print("📺 Using fallback CNN schedule")
            return get_cnn_fallback_schedule()

    except Exception as e:
        print(f"⚠️  Error fetching CNN schedule: {e}")
        print("📺 Using fallback CNN schedule")
        return get_cnn_fallback_schedule()

def get_cnn_fallback_schedule():
    """Fallback CNN schedule based on typical programming"""
    now = datetime.now()
    current_hour = now.hour

    # CNN typical programming schedule
    if 0 <= current_hour < 4:
        schedule = [
            {"start": "12:00 AM", "duration": 60, "title": "CNN Tonight", "description": "Late night news coverage and analysis."},
            {"start": "1:00 AM", "duration": 60, "title": "CNN Newsroom", "description": "Breaking news and top stories from around the world."},
            {"start": "2:00 AM", "duration": 60, "title": "CNN Newsroom", "description": "Breaking news and top stories from around the world."},
            {"start": "3:00 AM", "duration": 60, "title": "Early Start", "description": "Early morning news to start your day."},
        ]
    elif 4 <= current_hour < 9:
        schedule = [
            {"start": "4:00 AM", "duration": 120, "title": "Early Start", "description": "Early morning news to start your day."},
            {"start": "6:00 AM", "duration": 180, "title": "CNN News Central", "description": "Morning news with the latest headlines."},
        ]
    elif 9 <= current_hour < 13:
        schedule = [
            {"start": "9:00 AM", "duration": 60, "title": "CNN News Central", "description": "Morning news with the latest headlines."},
            {"start": "10:00 AM", "duration": 60, "title": "CNN Newsroom", "description": "Breaking news and top stories from around the world."},
            {"start": "11:00 AM", "duration": 60, "title": "Inside Politics", "description": "Political news and analysis with John King."},
            {"start": "12:00 PM", "duration": 60, "title": "Inside Politics", "description": "Political news and analysis with John King."},
        ]
    elif 13 <= current_hour < 16:
        schedule = [
            {"start": "1:00 PM", "duration": 60, "title": "CNN Newsroom", "description": "Breaking news and top stories from around the world."},
            {"start": "2:00 PM", "duration": 60, "title": "CNN Newsroom", "description": "Breaking news and top stories from around the world."},
            {"start": "3:00 PM", "duration": 60, "title": "The Lead with Jake Tapper", "description": "Afternoon news with Jake Tapper."},
        ]
    elif 16 <= current_hour < 20:
        schedule = [
            {"start": "4:00 PM", "duration": 60, "title": "The Lead with Jake Tapper", "description": "Afternoon news with Jake Tapper."},
            {"start": "5:00 PM", "duration": 60, "title": "The Situation Room", "description": "Evening news with Wolf Blitzer."},
            {"start": "6:00 PM", "duration": 60, "title": "The Situation Room", "description": "Evening news with Wolf Blitzer."},
            {"start": "7:00 PM", "duration": 60, "title": "Erin Burnett OutFront", "description": "Prime time news with Erin Burnett."},
        ]
    else:  # 20-24
        schedule = [
            {"start": "8:00 PM", "duration": 60, "title": "Anderson Cooper 360", "description": "Prime time news and interviews with Anderson Cooper."},
            {"start": "9:00 PM", "duration": 60, "title": "Anderson Cooper 360", "description": "Prime time news and interviews with Anderson Cooper."},
            {"start": "10:00 PM", "duration": 60, "title": "CNN Tonight", "description": "Late night news coverage and analysis."},
            {"start": "11:00 PM", "duration": 60, "title": "CNN Tonight", "description": "Late night news coverage and analysis."},
        ]

    return schedule

def get_espn_schedule():
    """Fetch ESPN schedule"""
    try:
        print("🔍 Fetching ESPN schedule from ESPN.com...")
        url = "https://www.espn.com/watch/schedule"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        schedule = []

        # ESPN schedule parsing
        items = soup.find_all(['div', 'article'], class_=re.compile(r'schedule|event|game', re.I))

        for item in items[:8]:
            time_elem = item.find(['span', 'time'], string=re.compile(r'\d{1,2}:\d{2}', re.I))
            title_elem = item.find(['h3', 'h4', 'span'], class_=re.compile(r'title|name', re.I))
            desc_elem = item.find(['p', 'span'], class_=re.compile(r'desc|detail', re.I))

            if time_elem and title_elem:
                time_text = time_elem.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', time_text, re.I)

                if time_match:
                    hours = time_match.group(1)
                    mins = time_match.group(2)
                    period = time_match.group(3).upper() if time_match.group(3) else 'PM'

                    schedule.append({
                        'start': f"{hours}:{mins} {period}",
                        'duration': 120,
                        'title': title_elem.get_text(strip=True)[:100],
                        'description': desc_elem.get_text(strip=True)[:200] if desc_elem else "Live sports coverage."
                    })

        if schedule:
            print(f"✅ Found {len(schedule)} ESPN shows")
            return schedule[:8]
    except Exception as e:
        print(f"⚠️  Error fetching ESPN: {e}")

    # Fallback
    return [
        {"start": "12:00 PM", "duration": 30, "title": "SportsCenter", "description": "Your home for sports news, highlights, and analysis."},
        {"start": "12:30 PM", "duration": 30, "title": "NFL Live", "description": "NFL news, analysis, and insider information."},
        {"start": "1:00 PM", "duration": 60, "title": "NBA Today", "description": "Breaking NBA news and game previews."},
        {"start": "2:00 PM", "duration": 120, "title": "College Football", "description": "Live college football coverage."},
    ]

def get_fox_schedule():
    """Fetch FOX schedule"""
    try:
        print("🔍 Fetching FOX schedule from FOX.com...")
        url = "https://www.fox.com/schedule/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        schedule = []

        items = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'schedule|show|program', re.I))

        for item in items[:8]:
            time_elem = item.find(['span', 'time'], string=re.compile(r'\d{1,2}:\d{2}', re.I))
            title_elem = item.find(['h2', 'h3', 'h4'])

            if time_elem and title_elem:
                time_text = time_elem.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_text, re.I)

                if time_match:
                    schedule.append({
                        'start': f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3).upper()}",
                        'duration': 30,
                        'title': title_elem.get_text(strip=True)[:100],
                        'description': "FOX primetime entertainment."
                    })

        if schedule:
            print(f"✅ Found {len(schedule)} FOX shows")
            return schedule[:8]
    except Exception as e:
        print(f"⚠️  Error fetching FOX: {e}")

    # Fallback
    return [
        {"start": "12:00 PM", "duration": 30, "title": "The Simpsons", "description": "Animated sitcom about the Simpson family."},
        {"start": "12:30 PM", "duration": 30, "title": "Bob's Burgers", "description": "Animated comedy about a family-run restaurant."},
        {"start": "1:00 PM", "duration": 60, "title": "NFL on FOX", "description": "NFL football coverage and analysis."},
        {"start": "2:00 PM", "duration": 120, "title": "FOX Sports", "description": "Sports coverage and highlights."},
    ]

def get_nbc_schedule():
    """Fetch NBC schedule"""
    try:
        print("🔍 Fetching NBC schedule from NBC.com...")
        url = "https://www.nbc.com/schedule"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        schedule = []

        items = soup.find_all(['div', 'article'], class_=re.compile(r'schedule|show', re.I))

        for item in items[:8]:
            time_elem = item.find(['span', 'time'])
            title_elem = item.find(['h2', 'h3', 'h4'])

            if time_elem and title_elem:
                time_text = time_elem.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_text, re.I)

                if time_match:
                    schedule.append({
                        'start': f"{time_match.group(1)}:{time_match.group(2)} {time_match.group(3).upper()}",
                        'duration': 60,
                        'title': title_elem.get_text(strip=True)[:100],
                        'description': "NBC programming."
                    })

        if schedule:
            print(f"✅ Found {len(schedule)} NBC shows")
            return schedule[:8]
    except Exception as e:
        print(f"⚠️  Error fetching NBC: {e}")

    # Fallback
    return [
        {"start": "12:00 PM", "duration": 60, "title": "Days of Our Lives", "description": "Long-running daytime soap opera."},
        {"start": "1:00 PM", "duration": 60, "title": "NBC News Daily", "description": "Midday news and current events."},
        {"start": "2:00 PM", "duration": 60, "title": "NBC Nightly News", "description": "Evening news with Lester Holt."},
        {"start": "3:00 PM", "duration": 60, "title": "The Kelly Clarkson Show", "description": "Talk show with Kelly Clarkson."},
    ]

def get_pbs_schedule():
    """Fetch PBS schedule"""
    try:
        print("🔍 Fetching PBS schedule from PBS.org...")
        url = "https://www.pbs.org/schedules/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        schedule = []

        # PBS schedule parsing - look for schedule items
        items = soup.find_all(['div', 'article', 'li'], class_=re.compile(r'schedule|program|show|listing', re.I))

        for item in items[:8]:
            # Look for time
            time_elem = item.find(['span', 'time'], string=re.compile(r'\d{1,2}:\d{2}', re.I))
            if not time_elem:
                time_elem = item.find(['span', 'time'], class_=re.compile(r'time|hour', re.I))

            # Look for title
            title_elem = item.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|headline', re.I))
            if not title_elem:
                title_elem = item.find(['h2', 'h3', 'h4', 'a'])

            # Look for description
            desc_elem = item.find(['p', 'div', 'span'], class_=re.compile(r'desc|summary|detail', re.I))

            if time_elem and title_elem:
                time_text = time_elem.get_text(strip=True)
                time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', time_text, re.I)

                if time_match:
                    hours = time_match.group(1)
                    mins = time_match.group(2)
                    period = time_match.group(3).upper() if time_match.group(3) else 'PM'

                    schedule.append({
                        'start': f"{hours}:{mins} {period}",
                        'duration': 60,
                        'title': title_elem.get_text(strip=True)[:100],
                        'description': desc_elem.get_text(strip=True)[:200] if desc_elem else "PBS educational programming."
                    })

        if schedule:
            print(f"✅ Found {len(schedule)} PBS shows")
            return schedule[:8]
    except Exception as e:
        print(f"⚠️  Error fetching PBS: {e}")

    # Fallback
    return [
        {"start": "12:00 PM", "duration": 60, "title": "PBS NewsHour", "description": "In-depth news coverage and analysis."},
        {"start": "1:00 PM", "duration": 60, "title": "Masterpiece", "description": "British dramas and period pieces."},
        {"start": "2:00 PM", "duration": 60, "title": "NOVA", "description": "Science documentaries exploring the natural world."},
        {"start": "3:00 PM", "duration": 60, "title": "Antiques Roadshow", "description": "Appraisals of antiques and collectibles."},
    ]

def get_channel_schedules():
    """Get schedules for all channels"""
    channels = {
        "CNN": {
            "name": "CNN",
            "schedule": get_cnn_schedule()
        },
        "ESPN": {
            "name": "ESPN",
            "schedule": get_espn_schedule()
        },
        "FOX": {
            "name": "FOX",
            "schedule": get_fox_schedule()
        },
        "NBC": {
            "name": "NBC",
            "schedule": get_nbc_schedule()
        },
        "PBS": {
            "name": "PBS",
            "schedule": get_pbs_schedule()
        },
        "NFLX1": {
            "name": "Netflix 1",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "Stranger Things", "description": "Sci-fi horror series set in 1980s Indiana."},
                {"start": "1:00 PM", "duration": 60, "title": "The Crown", "description": "Drama chronicling the reign of Queen Elizabeth II."},
                {"start": "2:00 PM", "duration": 120, "title": "Movie: Glass Onion", "description": "A detective investigates a murder mystery on a private island."},
            ]
        },
        "HBO1": {
            "name": "HBO 1",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "House of the Dragon", "description": "Prequel to Game of Thrones set 200 years earlier."},
                {"start": "1:00 PM", "duration": 30, "title": "Last Week Tonight", "description": "Satirical news and current events with John Oliver."},
                {"start": "1:30 PM", "duration": 30, "title": "Real Time with Bill Maher", "description": "Political talk show with Bill Maher."},
                {"start": "2:00 PM", "duration": 120, "title": "Movie: Dune Part Two", "description": "Epic sci-fi sequel following Paul Atreides' journey."},
            ]
        },
        "HULU1": {
            "name": "Hulu 1",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "The Handmaid's Tale", "description": "Dystopian drama based on Margaret Atwood's novel."},
                {"start": "1:00 PM", "duration": 30, "title": "Only Murders in the Building", "description": "Mystery comedy about true crime podcasters."},
                {"start": "1:30 PM", "duration": 30, "title": "The Bear", "description": "Drama about a chef running a Chicago sandwich shop."},
                {"start": "2:00 PM", "duration": 90, "title": "Movie: Poor Things", "description": "Fantasy comedy about a young woman brought back to life."},
            ]
        },
        "ATV+": {
            "name": "Apple TV+",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "Ted Lasso", "description": "Comedy about an American football coach in England."},
                {"start": "1:00 PM", "duration": 60, "title": "Severance", "description": "Sci-fi thriller about work-life separation technology."},
                {"start": "2:00 PM", "duration": 120, "title": "Movie: Killers of the Flower Moon", "description": "Crime drama about the Osage Nation murders."},
            ]
        },
        "P+": {
            "name": "Paramount+",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "Yellowstone", "description": "Western drama about the Dutton family ranch."},
                {"start": "1:00 PM", "duration": 30, "title": "Star Trek: Strange New Worlds", "description": "Sci-fi series exploring new worlds and civilizations."},
                {"start": "1:30 PM", "duration": 30, "title": "The Good Fight", "description": "Legal drama spin-off of The Good Wife."},
                {"start": "2:00 PM", "duration": 120, "title": "Movie: Top Gun: Maverick", "description": "Action sequel following Pete 'Maverick' Mitchell."},
            ]
        },
        "PCOK": {
            "name": "Peacock",
            "schedule": [
                {"start": "12:00 PM", "duration": 30, "title": "The Office (Rerun)", "description": "Mockumentary sitcom about office workers."},
                {"start": "12:30 PM", "duration": 30, "title": "Parks and Recreation", "description": "Comedy about a small-town parks department."},
                {"start": "1:00 PM", "duration": 60, "title": "Poker Face", "description": "Mystery series about a woman who can detect lies."},
                {"start": "2:00 PM", "duration": 90, "title": "Movie: Oppenheimer", "description": "Biographical thriller about J. Robert Oppenheimer."},
            ]
        },
        "ABC": {
            "name": "ABC Network",
            "schedule": [
                {"start": "12:00 PM", "duration": 60, "title": "General Hospital", "description": "Long-running medical drama and soap opera."},
                {"start": "1:00 PM", "duration": 60, "title": "GMA3: What You Need to Know", "description": "Afternoon news and lifestyle show."},
                {"start": "2:00 PM", "duration": 60, "title": "ABC News Live", "description": "Breaking news and current events."},
                {"start": "3:00 PM", "duration": 60, "title": "Jeopardy!", "description": "Classic game show with trivia questions."},
            ]
        },
    }

    return channels

def load_existing_channels():
    """Load existing channels from guide.xml if it exists"""
    if not os.path.exists('guide.xml'):
        return {}

    try:
        tree = ET.parse('guide.xml')
        root = tree.getroot()
        existing = {}

        for channel in root.findall('.//channel'):
            channel_num = channel.find('number').text
            channel_name = channel.find('name').text
            shows_elem = channel.find('shows')

            schedule = []
            for show in shows_elem.findall('show'):
                schedule.append({
                    'start': show.get('start'),
                    'duration': int(show.get('duration')),
                    'title': show.text,
                    'description': show.get('description', '')
                })

            existing[channel_num] = {
                'name': channel_name,
                'schedule': schedule
            }

        return existing
    except Exception as e:
        print(f"⚠️  Could not load existing guide.xml: {e}")
        return {}

def update_guide_xml():
    """Update guide.xml with new/updated channels, preserving existing ones"""

    # Load existing channels
    existing_channels = load_existing_channels()
    print(f"📂 Loaded {len(existing_channels)} existing channels")

    # Get new channel data
    new_channel_data = get_channel_schedules()

    # Merge: new data overwrites existing, but we keep channels not in new_channel_data
    merged_channels = existing_channels.copy()
    added = []
    updated = []

    for channel_num, channel_info in new_channel_data.items():
        if channel_num in merged_channels:
            updated.append(channel_num)
        else:
            added.append(channel_num)
        merged_channels[channel_num] = channel_info

    # Create root element
    root = ET.Element('guide')

    # Add current date
    date_elem = ET.SubElement(root, 'date')
    date_elem.text = datetime.now().strftime("%m/%d/%y")

    # Add ad section
    ad = ET.SubElement(root, 'ad')
    ad_text = ET.SubElement(ad, 'text')
    ad_text.text = "Call 1-800-CABLE-TV for Premium Channels!"

    # Add time slots
    timeslots = ET.SubElement(root, 'timeslots')
    for slot in get_current_time_slots():
        time_elem = ET.SubElement(timeslots, 'time')
        time_elem.text = slot

    # Add all merged channels
    channels_elem = ET.SubElement(root, 'channels')

    for channel_num, channel_info in merged_channels.items():
        channel = ET.SubElement(channels_elem, 'channel')

        number = ET.SubElement(channel, 'number')
        number.text = channel_num

        name = ET.SubElement(channel, 'name')
        name.text = channel_info['name']

        shows = ET.SubElement(channel, 'shows')
        for show in channel_info['schedule']:
            show_elem = ET.SubElement(shows, 'show')
            show_elem.set('start', show['start'])
            show_elem.set('duration', str(show['duration']))
            if 'description' in show and show['description']:
                show_elem.set('description', show['description'])
            show_elem.text = show['title']

    # Pretty print XML
    xml_str = ET.tostring(root, encoding='unicode')
    dom = xml.dom.minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')

    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)

    # Write to file
    with open('guide.xml', 'w', encoding='utf-8') as f:
        f.write(pretty_xml)

    print("\n✅ guide.xml updated successfully!")
    print(f"📺 Total channels: {len(merged_channels)}")
    if added:
        print(f"➕ Added: {', '.join(added)}")
    if updated:
        print(f"🔄 Updated: {', '.join(updated)}")
    print(f"🕐 Time slots: {', '.join(get_current_time_slots()[:4])}...")

if __name__ == "__main__":
    update_guide_xml()
