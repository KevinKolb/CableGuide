#!/usr/bin/env python3
"""
NFL Network TV Schedule Scraper
Fetches NFL Network programming schedule and creates/updates guide.xml in XMLTV format.
Covers from 3 hours ago until 8 days from now (or whatever data is available).
"""

import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import sys
from typing import List, Dict
import re

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    print("Warning: BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
    HAS_BS4 = False


class NFLNetworkScheduleFetcher:
    """Fetches and processes NFL Network TV schedule data."""

    def __init__(self):
        self.channel_id = "nflnetwork.us"
        self.channel_name = "NFL Network"
        self.programs = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_schedule_tvguide(self) -> List[Dict]:
        """
        Fetch schedule from TV Guide website.
        Alternative reliable source for NFL Network schedule.
        """
        programs = []
        base_url = "https://www.tvguide.com/listings/nfl-network/"

        try:
            print(f"Fetching NFL Network schedule from TVGuide...")
            response = self.session.get(base_url, timeout=30)
            response.raise_for_status()

            if not HAS_BS4:
                print("Cannot parse HTML without BeautifulSoup4")
                return programs

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parse schedule listings (TVGuide structure may vary)
            listings = soup.find_all('div', class_=re.compile('listing|program|show'))

            for listing in listings[:100]:  # Limit to reasonable number
                try:
                    # Extract time, title, description
                    time_elem = listing.find(class_=re.compile('time|airtime'))
                    title_elem = listing.find(class_=re.compile('title|name'))
                    desc_elem = listing.find(class_=re.compile('desc|synopsis'))

                    if time_elem and title_elem:
                        programs.append({
                            'start': time_elem.get_text(strip=True),
                            'title': title_elem.get_text(strip=True),
                            'desc': desc_elem.get_text(strip=True) if desc_elem else ''
                        })
                except Exception as e:
                    continue

            print(f"Found {len(programs)} programs from TVGuide")

        except Exception as e:
            print(f"Error fetching from TVGuide: {e}")

        return programs

    def generate_mock_schedule(self) -> List[Dict]:
        """
        Generate a mock NFL Network schedule for testing/demonstration.
        Uses typical NFL Network programming patterns.
        """
        programs = []

        # Start from 3 hours ago, rounded to nearest hour
        now = datetime.now()
        start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)

        # Typical NFL Network programming blocks
        nfl_shows = [
            {"title": "Good Morning Football", "duration": 240, "desc": "Morning NFL talk and analysis"},
            {"title": "NFL Total Access", "duration": 60, "desc": "Inside look at the NFL"},
            {"title": "NFL GameDay Live", "duration": 60, "desc": "Pre-game coverage and analysis"},
            {"title": "NFL Films Presents", "duration": 60, "desc": "NFL Films documentary series"},
            {"title": "America's Game", "duration": 60, "desc": "Championship team retrospectives"},
            {"title": "A Football Life", "duration": 60, "desc": "NFL player and coach documentaries"},
            {"title": "NFL Top 10", "duration": 30, "desc": "Countdown of NFL's greatest moments"},
            {"title": "Sound FX", "duration": 30, "desc": "NFL games with enhanced audio"},
            {"title": "NFL GameDay Morning", "duration": 180, "desc": "Sunday morning pre-game show"},
            {"title": "NFL GameDay Kickoff", "duration": 120, "desc": "Pre-game analysis and predictions"},
            {"title": "NFL GameDay Final", "duration": 60, "desc": "Post-game highlights and reaction"},
            {"title": "NFL GameDay Prime", "duration": 60, "desc": "Prime time game preview"},
            {"title": "Thursday Night Football", "duration": 210, "desc": "Live NFL game", "category": "Sports"},
            {"title": "NFL Replay", "duration": 120, "desc": "Condensed replay of recent game"},
            {"title": "NFL RedZone", "duration": 420, "desc": "Live game coverage of red zone plays", "category": "Sports"},
            {"title": "Inside Training Camp", "duration": 60, "desc": "Training camp coverage"},
            {"title": "Path to the Draft", "duration": 120, "desc": "NFL Draft analysis and coverage"},
            {"title": "NFL Fantasy Live", "duration": 60, "desc": "Fantasy football analysis"},
        ]

        current_time = start_time
        end_time = now + timedelta(days=8)

        show_index = 0
        while current_time < end_time:
            # Vary programming based on day and time
            hour = current_time.hour
            is_weekend = current_time.weekday() in [5, 6]  # Saturday, Sunday
            is_thursday = current_time.weekday() == 3

            # Early morning (12am-6am): Replays and Films
            if 0 <= hour < 6:
                show = nfl_shows[show_index % 4 + 3]  # Films, America's Game, etc.
            # Morning (6am-10am): Good Morning Football
            elif 6 <= hour < 10:
                show = nfl_shows[0]  # Good Morning Football
            # Late morning/Afternoon (10am-5pm)
            elif 10 <= hour < 17:
                if is_weekend:
                    # Sunday: GameDay coverage
                    if current_time.weekday() == 6 and 9 <= hour < 12:
                        show = nfl_shows[8]  # NFL GameDay Morning
                    elif current_time.weekday() == 6 and 12 <= hour < 13:
                        show = nfl_shows[9]  # NFL GameDay Kickoff
                    elif current_time.weekday() == 6 and 13 <= hour < 20:
                        show = nfl_shows[14]  # NFL RedZone
                    else:
                        show = nfl_shows[show_index % 3 + 1]  # Total Access, etc.
                else:
                    show = nfl_shows[show_index % 5 + 1]  # Various shows
            # Evening (5pm-8pm)
            elif 17 <= hour < 20:
                if is_weekend and current_time.weekday() == 6:
                    show = nfl_shows[10]  # NFL GameDay Final
                else:
                    show = nfl_shows[11]  # NFL GameDay Prime
            # Prime time (8pm-11pm)
            elif 20 <= hour < 23:
                if is_thursday:
                    show = nfl_shows[12]  # Thursday Night Football
                else:
                    show = nfl_shows[13]  # NFL Replay
            # Late night (11pm-12am)
            else:
                show = nfl_shows[1]  # NFL Total Access

            program = {
                'start': current_time,
                'stop': current_time + timedelta(minutes=show['duration']),
                'title': show['title'],
                'desc': show['desc']
            }

            if 'category' in show:
                program['category'] = show['category']

            programs.append(program)

            current_time += timedelta(minutes=show['duration'])
            show_index += 1

        print(f"Generated {len(programs)} mock program entries")
        return programs

    def fetch_all_sources(self, use_mock=False) -> List[Dict]:
        """
        Try multiple sources to get the most complete schedule.
        NEVER generates fake/mock data - only returns real schedule data.
        """
        if use_mock:
            print("ERROR: Mock mode not supported. This script only fetches real data.")
            print("For real data sources:")
            print("  - Schedules Direct subscription ($35/year): https://www.schedulesdirect.org/")
            print("  - TvProfil XMLTV: https://tvprofil.net/xmltv/")
            return []

        programs = []

        # Try TV Guide first
        programs = self.fetch_schedule_tvguide()

        # If still no data, fail - don't generate fake data
        if not programs:
            print("ERROR: All external sources failed. No real data available.")
            print("This script will NOT generate fake/mock data.")
            print("For real data, you need:")
            print("  - Schedules Direct subscription ($35/year): https://www.schedulesdirect.org/")
            print("  - Commercial TV guide API access")
            print("  - VPN if region-blocked")

        return programs


class XMLTVGenerator:
    """Generates and updates XMLTV format guide.xml file."""

    def __init__(self, filename='guide.xml'):
        # If running from scripts folder, save to parent directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)

        # If filename is relative, save to parent directory
        if not os.path.isabs(filename):
            self.filename = os.path.join(parent_dir, filename)
        else:
            self.filename = filename

        self.tree = None
        self.root = None
        self.load_or_create()

    def load_or_create(self):
        """Load existing guide.xml or create new one."""
        if os.path.exists(self.filename):
            try:
                self.tree = ET.parse(self.filename)
                self.root = self.tree.getroot()
                print(f"Loaded existing {self.filename}")
            except Exception as e:
                print(f"Error loading {self.filename}: {e}")
                self.create_new()
        else:
            self.create_new()

    def create_new(self):
        """Create new XMLTV structure."""
        self.root = ET.Element('tv')
        self.root.set('generator-info-name', 'NFL Network Schedule Scraper')
        self.root.set('generator-info-url', 'https://github.com/yourusername/CableGuide')
        self.tree = ET.ElementTree(self.root)
        print(f"Created new {self.filename} structure")

    def download_logo(self, logo_url: str, logo_filename: str) -> str:
        """Download logo to logos folder and return local path."""
        # Get parent directory (CableGuide root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        logos_dir = os.path.join(parent_dir, 'logos')

        # Create logos directory if it doesn't exist
        os.makedirs(logos_dir, exist_ok=True)

        logo_path = os.path.join(logos_dir, logo_filename)

        # Download if not already exists
        if not os.path.exists(logo_path):
            try:
                print(f"Downloading logo from {logo_url}...")
                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()

                with open(logo_path, 'wb') as f:
                    f.write(response.content)

                print(f"Saved logo to {logo_filename}")
            except Exception as e:
                print(f"Failed to download logo: {e}")
                return logo_url  # Fallback to original URL

        # Return relative path from guide.xml location
        return f"logos/{logo_filename}"

    def ensure_channel(self, channel_id: str, channel_name: str, logo_url: str = None, logo_filename: str = None):
        """Ensure channel element exists in XML."""
        # Check if channel already exists
        for channel in self.root.findall('channel'):
            if channel.get('id') == channel_id:
                return

        # Create channel element
        channel = ET.SubElement(self.root, 'channel')
        channel.set('id', channel_id)

        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = channel_name

        if logo_url:
            if logo_filename:
                # Download logo and use local path
                icon_src = self.download_logo(logo_url, logo_filename)
            else:
                # Use remote URL directly
                icon_src = logo_url
            icon = ET.SubElement(channel, 'icon')
            icon.set('src', icon_src)

        print(f"Added channel: {channel_name} ({channel_id})")

    def format_xmltv_time(self, dt: datetime) -> str:
        """Format datetime to XMLTV format: YYYYMMDDHHmmss +TZTZ."""
        # Get timezone offset
        offset = dt.strftime('%z')
        if not offset:
            offset = '+0000'

        return dt.strftime('%Y%m%d%H%M%S') + ' ' + offset

    def remove_channel_programs_in_range(self, channel_id: str, start_time: datetime, end_time: datetime):
        """Remove all programs for a channel within the specified date range."""
        programs_to_remove = []

        for programme in self.root.findall('programme'):
            if programme.get('channel') != channel_id:
                continue

            # Parse start time
            start_str = programme.get('start', '')
            try:
                # Extract just the datetime part (before timezone)
                prog_start = datetime.strptime(start_str[:14], '%Y%m%d%H%M%S')

                # Check if this program falls within our date range
                if start_time <= prog_start <= end_time:
                    programs_to_remove.append(programme)
            except:
                continue

        # Remove marked programs
        for prog in programs_to_remove:
            self.root.remove(prog)

        if programs_to_remove:
            print(f"Removed {len(programs_to_remove)} existing {channel_id} programs in date range")

    def add_program(self, channel_id: str, program: Dict):
        """Add a program to the guide."""
        prog = ET.SubElement(self.root, 'programme')
        prog.set('channel', channel_id)
        prog.set('start', self.format_xmltv_time(program['start']))
        prog.set('stop', self.format_xmltv_time(program['stop']))

        title = ET.SubElement(prog, 'title')
        title.set('lang', 'en')
        title.text = program['title']

        if program.get('desc'):
            desc = ET.SubElement(prog, 'desc')
            desc.set('lang', 'en')
            desc.text = program['desc']

        if program.get('category'):
            cat = ET.SubElement(prog, 'category')
            cat.set('lang', 'en')
            cat.text = program['category']

    def update_with_programs(self, channel_id: str, channel_name: str, programs: List[Dict],
                            logo_url: str = None, logo_filename: str = None):
        """
        Update guide with new programs.
        Removes all existing programs for this channel in the date range, then adds new ones.
        This prevents duplicates.
        """
        if not programs:
            print("No programs to add")
            return

        # Ensure channel exists
        self.ensure_channel(channel_id, channel_name, logo_url, logo_filename)

        # Determine the date range covered by these programs
        start_time = min(p['start'] for p in programs)
        end_time = max(p['stop'] for p in programs)

        print(f"Updating {channel_name} schedule:")
        print(f"  From: {start_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  To:   {end_time.strftime('%Y-%m-%d %H:%M')}")

        # Remove ALL existing programs for this channel in this date range
        self.remove_channel_programs_in_range(channel_id, start_time, end_time)

        # Add all new programs
        for program in programs:
            self.add_program(channel_id, program)

        print(f"Added {len(programs)} programs")

    def sort_programs(self):
        """Sort all programs by channel ID, then by start time."""
        programs = list(self.root.findall('programme'))

        # Remove all programs from root
        for prog in programs:
            self.root.remove(prog)

        # Sort programs by channel, then start time
        def get_sort_key(prog):
            channel = prog.get('channel', '')
            start = prog.get('start', '')
            return (channel, start)

        programs.sort(key=get_sort_key)

        # Re-add programs in sorted order
        for prog in programs:
            self.root.append(prog)

        print("Sorted programs by channel and time")

    def prettify(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')

    def save(self):
        """Save the XML to file with pretty formatting."""
        try:
            # Sort programs before saving
            self.sort_programs()

            # Pretty print
            xml_str = self.prettify(self.root)

            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(xml_str)

            print(f"Saved {self.filename}")

            # Show file size
            size = os.path.getsize(self.filename)
            print(f"File size: {size:,} bytes")

        except Exception as e:
            print(f"Error saving {self.filename}: {e}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("NFL Network TV Schedule Scraper")
    print("=" * 60)
    print()

    # Check for mock mode - NOT SUPPORTED
    use_mock = '--mock' in sys.argv or '-m' in sys.argv

    if use_mock:
        print("WARNING: Mock mode not supported in this script.")
        print("This script only fetches REAL data, never fake/generated data.")
        print()

    # Initialize fetcher
    fetcher = NFLNetworkScheduleFetcher()

    # Fetch schedule from all available sources
    programs = fetcher.fetch_all_sources(use_mock=use_mock)

    if not programs:
        print("Failed to fetch any schedule data")
        return 1

    # Initialize/load XML guide
    xml_guide = XMLTVGenerator('guide.xml')

    # Update guide with NFL Network programs
    # Check if logo exists locally, otherwise download
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    local_logo = os.path.join(parent_dir, 'logos', 'NFL_Network_logo.svg')

    if os.path.exists(local_logo):
        # Use existing local logo
        xml_guide.update_with_programs(
            channel_id='nflnetwork.us',
            channel_name='NFL Network',
            programs=programs,
            logo_url='logos/NFL_Network_logo.svg',
            logo_filename=None  # Already exists locally
        )
    else:
        # Download from Wikipedia (fallback)
        xml_guide.update_with_programs(
            channel_id='nflnetwork.us',
            channel_name='NFL Network',
            programs=programs,
            logo_url='https://upload.wikimedia.org/wikipedia/en/8/8f/NFL_Network_logo.svg',
            logo_filename='NFL_Network_logo.svg'
        )

    # Save updated guide
    xml_guide.save()

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  - Install dependencies: pip install requests beautifulsoup4")
    print("  - Run with real data: python scripts/pull_nfl_network.py")
    print("  - Run with mock data: python scripts/pull_nfl_network.py --mock")
    print()
    print("For reliable data sources:")
    print("  - Schedules Direct: https://www.schedulesdirect.org/ ($35/year)")
    print("  - TvProfil XMLTV: https://tvprofil.net/xmltv/")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
