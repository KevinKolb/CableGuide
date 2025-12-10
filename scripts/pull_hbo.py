#!/usr/bin/env python3
"""
HBO TV Schedule Scraper
Fetches HBO programming schedule and creates/updates guide.xml in XMLTV format.
Covers from 3 hours ago until 8 days from now (or whatever data is available).
"""

import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import sys
from typing import List, Dict


class HBOScheduleFetcher:
    """Fetches and processes HBO TV schedule data."""

    def __init__(self):
        self.channel_id = "hbo.us"
        self.channel_name = "HBO"
        self.programs = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_schedule_epgpw(self, channel_id: str = "464745") -> List[Dict]:
        """
        Fetch schedule from EPG.pw API.
        Gets HBO shows and their airtimes from the free EPG.pw service.

        Default channel_id 464745 is HBO East.
        Other HBO channels:
        - 465249: HBO (Pacific)
        - 464953: HBO Comedy HD
        - 465201: HBO Drama
        - 464745: HBO East (default)
        - 465255: HBO Hits
        - 464960: HBO Latino HD
        - 480609: HBO Movies
        - 465279: HBO Signature HD
        - 465302: HBO West
        - 465104: HBO Zone HD
        - 465146: HBO2 (Pacific)
        - 465041: HBO2 HD
        - 464985: HBO2 HD (Pacific)
        """
        programs = []

        try:
            print(f"Fetching HBO schedule from EPG.pw API (channel {channel_id})...")

            # EPG.pw API endpoint
            url = f"https://epg.pw/api/epg.xml?channel_id={channel_id}"

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Extract programs from XMLTV format
            for programme in root.findall('programme'):
                try:
                    # Get start and stop times (XMLTV format: YYYYMMDDHHmmss +TZTZ)
                    start_str = programme.get('start', '')
                    stop_str = programme.get('stop', '')

                    # Parse times (format: "20251210050000 +0800")
                    start = self.parse_xmltv_time(start_str)
                    stop = self.parse_xmltv_time(stop_str)

                    if not start or not stop:
                        continue

                    # Get title
                    title_elem = programme.find('title')
                    title = title_elem.text if title_elem is not None and title_elem.text else 'Untitled'

                    # Get description
                    desc_elem = programme.find('desc')
                    desc = desc_elem.text if desc_elem is not None and desc_elem.text else ''

                    # Get category
                    category_elem = programme.find('category')
                    category = category_elem.text if category_elem is not None and category_elem.text else None

                    program = {
                        'start': start,
                        'stop': stop,
                        'title': title,
                        'desc': desc
                    }

                    if category:
                        program['category'] = category

                    programs.append(program)

                except Exception as e:
                    print(f"  Error parsing program: {e}")
                    continue

            # Sort by start time
            programs.sort(key=lambda p: p['start'])

            print(f"Found {len(programs)} HBO programs from EPG.pw")

        except Exception as e:
            print(f"Error fetching from EPG.pw: {e}")

        return programs

    def parse_xmltv_time(self, time_str: str) -> datetime:
        """
        Parse XMLTV time format (YYYYMMDDHHmmss +TZTZ) to datetime.
        Example: "20251210050000 +0800"
        """
        try:
            # Split date/time from timezone
            parts = time_str.split()
            if len(parts) != 2:
                return None

            dt_str, tz_str = parts

            # Parse datetime (YYYYMMDDHHmmss)
            dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')

            # Parse timezone offset (+HHMM or -HHMM)
            if tz_str[0] in ['+', '-']:
                sign = 1 if tz_str[0] == '+' else -1
                hours = int(tz_str[1:3])
                minutes = int(tz_str[3:5])

                # Convert to local time by subtracting the offset
                # (the time is given in that timezone, we want local time)
                offset = timedelta(hours=sign * hours, minutes=sign * minutes)
                dt = dt - offset

            return dt

        except Exception as e:
            print(f"  Error parsing time '{time_str}': {e}")
            return None

    def generate_mock_schedule(self) -> List[Dict]:
        """
        Generate a mock HBO schedule for testing/demonstration.
        Uses typical HBO programming patterns.
        """
        programs = []

        # Start from 3 hours ago, rounded to nearest hour
        now = datetime.now()
        start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)

        # Typical HBO programming blocks - mix of series, movies, documentaries
        hbo_shows = [
            {"title": "The Last of Us", "duration": 60, "desc": "Post-apocalyptic drama series", "category": "Series"},
            {"title": "Succession", "duration": 60, "desc": "Drama about a media dynasty", "category": "Series"},
            {"title": "The White Lotus", "duration": 60, "desc": "Dark comedy anthology series", "category": "Series"},
            {"title": "House of the Dragon", "duration": 70, "desc": "Game of Thrones prequel series", "category": "Series"},
            {"title": "True Detective", "duration": 60, "desc": "Anthology crime drama series", "category": "Series"},
            {"title": "Euphoria", "duration": 60, "desc": "Teen drama series", "category": "Series"},
            {"title": "The Gilded Age", "duration": 60, "desc": "Period drama series", "category": "Series"},
            {"title": "Curb Your Enthusiasm", "duration": 30, "desc": "Comedy series with Larry David", "category": "Comedy"},
            {"title": "Last Week Tonight with John Oliver", "duration": 30, "desc": "News satire show", "category": "Talk"},
            {"title": "Real Time with Bill Maher", "duration": 60, "desc": "Political talk show", "category": "Talk"},
            {"title": "HBO Original Movie", "duration": 120, "desc": "Exclusive HBO original film", "category": "Movie"},
            {"title": "Blockbuster Movie", "duration": 150, "desc": "Recent theatrical release", "category": "Movie"},
            {"title": "Classic HBO Movie", "duration": 120, "desc": "Popular film from HBO library", "category": "Movie"},
            {"title": "HBO Documentary", "duration": 90, "desc": "Award-winning documentary", "category": "Documentary"},
            {"title": "Vice", "duration": 30, "desc": "News and culture series", "category": "Documentary"},
            {"title": "Hard Knocks", "duration": 60, "desc": "NFL training camp documentary", "category": "Sports"},
            {"title": "24/7 Boxing", "duration": 30, "desc": "Boxing behind-the-scenes series", "category": "Sports"},
            {"title": "Comedy Special", "duration": 60, "desc": "Stand-up comedy special", "category": "Comedy"},
        ]

        current_time = start_time
        end_time = now + timedelta(days=8)

        show_index = 0
        while current_time < end_time:
            # Vary programming based on time of day
            hour = current_time.hour
            is_weekend = current_time.weekday() in [5, 6]  # Saturday, Sunday
            is_primetime = 20 <= hour < 23

            # Early morning (12am-6am): Movies
            if 0 <= hour < 6:
                show = hbo_shows[11 if show_index % 2 == 0 else 12]  # Movies
            # Morning (6am-12pm): Documentaries and older series
            elif 6 <= hour < 12:
                show = hbo_shows[show_index % 4 + 13]  # Docs, Vice, etc.
            # Afternoon (12pm-6pm): Movies and series
            elif 12 <= hour < 18:
                if show_index % 3 == 0:
                    show = hbo_shows[11]  # Movie
                else:
                    show = hbo_shows[show_index % 7]  # Series
            # Prime time (6pm-11pm): Premium series and new episodes
            elif is_primetime:
                if is_weekend:
                    # Weekend prime time: Mix of top series and movies
                    if show_index % 2 == 0:
                        show = hbo_shows[show_index % 4]  # Top series
                    else:
                        show = hbo_shows[10]  # HBO Original Movie
                else:
                    # Weeknight prime time: Top series
                    show = hbo_shows[show_index % 7]  # Premium series
            # Late evening (11pm-12am): Comedy or talk shows
            else:
                show = hbo_shows[7 if show_index % 2 == 0 else 8]  # Comedy/Talk

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

    def fetch_all_sources(self, channel_id: str = "464745") -> List[Dict]:
        """
        Fetch schedule from EPG.pw - a free EPG service.
        """
        programs = []

        # Fetch from EPG.pw API
        programs = self.fetch_schedule_epgpw(channel_id)

        # If still no data, fail
        if not programs:
            print("ERROR: EPG.pw API returned no data.")
            print("Please check your internet connection or try again later.")
            print()
            print("Alternative data sources:")
            print("  - Schedules Direct ($35/year): https://www.schedulesdirect.org/")

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
        self.root.set('generator-info-name', 'HBO Schedule Scraper')
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
    print("HBO TV Schedule Scraper")
    print("=" * 60)
    print()

    # Check for channel argument
    channel_id = "464745"  # Default: HBO East

    if '--channel' in sys.argv:
        try:
            idx = sys.argv.index('--channel')
            if idx + 1 < len(sys.argv):
                channel_id = sys.argv[idx + 1]
                print(f"Using channel ID: {channel_id}")
        except:
            pass

    # Initialize fetcher
    fetcher = HBOScheduleFetcher()

    # Fetch schedule from EPG.pw
    programs = fetcher.fetch_all_sources(channel_id=channel_id)

    if not programs:
        print("Failed to fetch any schedule data")
        return 1

    # Initialize/load XML guide
    xml_guide = XMLTVGenerator('guide.xml')

    # Update guide with HBO programs
    # Check if logo exists locally, otherwise download
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    local_logo = os.path.join(parent_dir, 'logos', 'HBO_logo.svg')

    if os.path.exists(local_logo):
        # Use existing local logo
        xml_guide.update_with_programs(
            channel_id='hbo.us',
            channel_name='HBO',
            programs=programs,
            logo_url='logos/HBO_logo.svg',
            logo_filename=None  # Already exists locally
        )
    else:
        # Download from Wikipedia (fallback)
        xml_guide.update_with_programs(
            channel_id='hbo.us',
            channel_name='HBO',
            programs=programs,
            logo_url='https://upload.wikimedia.org/wikipedia/commons/d/de/HBO_logo.svg',
            logo_filename='HBO_logo.svg'
        )

    # Save updated guide
    xml_guide.save()

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  - Install dependencies: pip install requests")
    print("  - Run with HBO East (default): python scripts/pull_hbo.py")
    print("  - Run with different HBO channel: python scripts/pull_hbo.py --channel 465302")
    print()
    print("Available HBO channel IDs:")
    print("  464745: HBO East (default)")
    print("  465302: HBO West")
    print("  465249: HBO (Pacific)")
    print("  464953: HBO Comedy HD")
    print("  465201: HBO Drama")
    print("  465255: HBO Hits")
    print("  464960: HBO Latino HD")
    print("  480609: HBO Movies")
    print("  465279: HBO Signature HD")
    print("  465104: HBO Zone HD")
    print("  465041: HBO2 HD")
    print()
    print("Data source: EPG.pw (https://epg.pw)")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
