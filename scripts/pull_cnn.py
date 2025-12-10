#!/usr/bin/env python3
"""
CNN TV Schedule Scraper
Fetches CNN programming schedule and creates/updates guide.xml in XMLTV format.
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
import time

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    print("Warning: BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
    HAS_BS4 = False

# Try to import Selenium
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    HAS_SELENIUM = True
except ImportError:
    print("Warning: Selenium not installed. Install with: pip install selenium")
    HAS_SELENIUM = False


class CNNScheduleFetcher:
    """Fetches and processes CNN TV schedule data."""

    def __init__(self):
        self.channel_id = "cnn.us"
        self.channel_name = "CNN"
        self.programs = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def fetch_schedule_cnn_selenium(self) -> List[Dict]:
        """
        Fetch schedule from CNN.com using Selenium.
        Official source: https://www.cnn.com/tv/schedule/cnn
        """
        if not HAS_SELENIUM:
            print("ERROR: Selenium not installed. Install with: pip install selenium")
            return []

        programs = []
        url = "https://www.cnn.com/tv/schedule/cnn"

        try:
            print(f"Fetching CNN schedule from {url} using Selenium...")

            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)

            try:
                # Load the page
                driver.get(url)

                # Wait for schedule content to load
                print("Waiting for page to load...")
                wait = WebDriverWait(driver, 20)

                # Give the page time to fully render
                time.sleep(5)

                # Get the page source and parse with BeautifulSoup
                page_source = driver.page_source

                # Debug: save HTML to file for inspection
                debug_html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cnn_debug.html')
                with open(debug_html_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"Saved page HTML to {debug_html_path} for debugging")

                if not HAS_BS4:
                    print("ERROR: BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
                    return programs

                soup = BeautifulSoup(page_source, 'html.parser')

                # Find schedule entries - CNN uses specific class names
                schedule_items = soup.find_all('div', class_='tv-schedule__entry')

                print(f"Found {len(schedule_items)} schedule entries on page")

                # Parse each program entry
                current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

                for item in schedule_items:
                    try:
                        # Extract start time
                        start_elem = item.find('div', class_='tv-schedule__entry-start')
                        # Extract end time
                        end_elem = item.find('div', class_='tv-schedule__entry-end')
                        # Extract title
                        title_elem = item.find('div', class_='tv-schedule__entry-title')
                        # Extract description
                        desc_elem = item.find('div', class_='tv-schedule__entry-description')

                        # Get text values
                        start_text = start_elem.get_text(strip=True) if start_elem else None
                        end_text = end_elem.get_text(strip=True) if end_elem else None
                        title_text = title_elem.get_text(strip=True) if title_elem else None
                        desc_text = desc_elem.get_text(strip=True) if desc_elem else ''

                        # Skip if we don't have basic info
                        if not start_text or not title_text:
                            continue

                        # Parse start time
                        start_time = self.parse_time_string(start_text, current_date)

                        if start_time:
                            # Parse end time if available, otherwise estimate duration
                            if end_text:
                                stop_time = self.parse_time_string(end_text, current_date)
                                # Handle case where end time is next day
                                if stop_time and stop_time < start_time:
                                    stop_time = self.parse_time_string(end_text, current_date + timedelta(days=1))
                            else:
                                stop_time = start_time + timedelta(minutes=60)

                            # If we couldn't parse end time, estimate
                            if not stop_time:
                                stop_time = start_time + timedelta(minutes=60)

                            programs.append({
                                'start': start_time,
                                'stop': stop_time,
                                'title': title_text,
                                'desc': desc_text
                            })

                    except Exception as e:
                        # Skip items we can't parse
                        continue

                print(f"Successfully parsed {len(programs)} programs from CNN.com")

            finally:
                driver.quit()

        except Exception as e:
            print(f"Error fetching from CNN.com: {e}")
            import traceback
            traceback.print_exc()

        return programs

    def parse_time_string(self, time_str: str, base_date: datetime) -> datetime:
        """
        Parse various time string formats to datetime.
        Handles formats like: "9:00 PM ET", "21:00", "9:00 PM", etc.
        """
        try:
            # Remove timezone indicators
            time_str = re.sub(r'\s*(ET|EST|EDT|PT|PST|PDT)\s*', '', time_str, flags=re.I)
            time_str = time_str.strip()

            # Try 12-hour format with AM/PM
            for fmt in ['%I:%M %p', '%I:%M%p', '%I%p']:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    return base_date.replace(hour=parsed_time.hour, minute=parsed_time.minute)
                except ValueError:
                    continue

            # Try 24-hour format
            for fmt in ['%H:%M', '%H%M']:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    return base_date.replace(hour=parsed_time.hour, minute=parsed_time.minute)
                except ValueError:
                    continue

        except Exception as e:
            pass

        return None

    def fetch_schedule_titantv(self) -> List[Dict]:
        """
        Fetch schedule from TitanTV.
        Another alternative source.
        """
        programs = []
        # TitanTV requires specific lineup IDs, would need configuration
        print("TitanTV fetching not yet implemented (requires lineup configuration)")
        return programs

    def generate_mock_schedule(self) -> List[Dict]:
        """
        Generate a mock CNN schedule for testing/demonstration.
        Uses typical CNN programming patterns.
        """
        programs = []

        # Start from 3 hours ago, rounded to nearest hour
        now = datetime.now()
        start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=3)

        # Typical CNN programming blocks
        cnn_shows = [
            {"title": "CNN News Central", "duration": 60, "desc": "Breaking news and top stories"},
            {"title": "Inside Politics", "duration": 60, "desc": "Political analysis and discussion"},
            {"title": "CNN Newsroom", "duration": 120, "desc": "Live news coverage"},
            {"title": "The Lead with Jake Tapper", "duration": 60, "desc": "News and political analysis"},
            {"title": "The Situation Room", "duration": 120, "desc": "Breaking news with Wolf Blitzer"},
            {"title": "Erin Burnett OutFront", "duration": 60, "desc": "Evening news program"},
            {"title": "Anderson Cooper 360", "duration": 60, "desc": "In-depth news analysis"},
            {"title": "The Source with Kaitlan Collins", "duration": 60, "desc": "News and interviews"},
            {"title": "CNN Tonight", "duration": 60, "desc": "Late evening news"},
            {"title": "Laura Coates Live", "duration": 60, "desc": "News and legal analysis"},
            {"title": "CNN Newsroom", "duration": 180, "desc": "Overnight news coverage"},
        ]

        current_time = start_time
        end_time = now + timedelta(days=8)

        show_index = 0
        while current_time < end_time:
            show = cnn_shows[show_index % len(cnn_shows)]

            programs.append({
                'start': current_time,
                'stop': current_time + timedelta(minutes=show['duration']),
                'title': show['title'],
                'desc': show['desc']
            })

            current_time += timedelta(minutes=show['duration'])
            show_index += 1

        print(f"Generated {len(programs)} mock program entries")
        return programs

    def fetch_all_sources(self, use_mock=False) -> List[Dict]:
        """
        Try multiple sources to get the most complete schedule.
        Tries CNN.com first (official source), then falls back to mock data if requested.
        """
        programs = []

        # Try CNN.com first with Selenium
        print("Attempting to fetch from CNN.com (official source)...")
        programs = self.fetch_schedule_cnn_selenium()

        # If no data and mock requested, generate mock data
        if not programs and use_mock:
            print("\nNo data from CNN.com, generating mock schedule as requested...")
            programs = self.generate_mock_schedule()

        # If still no data and mock not requested, fail
        if not programs and not use_mock:
            print("\nERROR: Failed to fetch schedule from CNN.com")
            print("You can:")
            print("  - Try again (website might be temporarily unavailable)")
            print("  - Run with --mock flag to generate sample data: python scripts/pull_cnn.py --mock")
            print("  - Check if you need to update Chrome/ChromeDriver")
            print("\nFor production use, consider:")
            print("  - Schedules Direct subscription ($35/year): https://www.schedulesdirect.org/")
            print("  - TvProfil XMLTV: https://tvprofil.net/xmltv/")

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
        self.root.set('generator-info-name', 'CNN Schedule Scraper')
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

    def get_program_key(self, channel_id: str, start: datetime) -> str:
        """Create a unique key for a program based on channel and start time."""
        return f"{channel_id}:{start.strftime('%Y%m%d%H%M%S')}"

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
        # Get all channels and programs
        channels = list(self.root.findall('channel'))
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
    print("CNN TV Schedule Scraper")
    print("=" * 60)
    print()

    # Check for mock mode (fallback if real data fails)
    use_mock = '--mock' in sys.argv or '-m' in sys.argv

    if use_mock:
        print("INFO: Mock mode enabled as fallback.")
        print("Will generate sample data if CNN.com scraping fails.")
        print()

    # Initialize fetcher
    fetcher = CNNScheduleFetcher()

    # Fetch schedule from all available sources
    programs = fetcher.fetch_all_sources(use_mock=use_mock)

    if not programs:
        print("Failed to fetch any schedule data")
        return 1

    # Initialize/load XML guide
    xml_guide = XMLTVGenerator('guide.xml')

    # Update guide with CNN programs
    xml_guide.update_with_programs(
        channel_id='cnn.us',
        channel_name='CNN',
        programs=programs,
        logo_url='https://upload.wikimedia.org/wikipedia/commons/b/b1/CNN.svg',
        logo_filename='CNN.svg'
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
    print("  - Run with real data: python scripts/pull_cnn.py")
    print("  - Run with mock data: python scripts/pull_cnn.py --mock")
    print()
    print("For reliable data sources:")
    print("  - Schedules Direct: https://www.schedulesdirect.org/ ($35/year)")
    print("  - TvProfil XMLTV: https://tvprofil.net/xmltv/")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
