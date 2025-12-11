#!/usr/bin/env python3
"""
ESPN TV Schedule Scraper
Fetches ESPN programming schedule from espn.com and updates guide.xml in XMLTV format.
"""

import os
import sys
import re
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import xml.etree.ElementTree as ET
from xml.dom import minidom

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    print("ERROR: BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
    HAS_BS4 = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    print("ERROR: Selenium not installed. Install with: pip install selenium")
    HAS_SELENIUM = False


class ESPNScheduleFetcher:
    """Fetches and processes ESPN TV schedule data."""

    def __init__(self):
        self.channel_id = "espn.us"
        self.channel_name = "ESPN"

    def fetch_schedule_espn_selenium(self) -> List[Dict]:
        """Fetch schedule from ESPN.com using Selenium."""
        if not HAS_SELENIUM:
            print("ERROR: Selenium not installed. Install with: pip install selenium")
            return []

        programs = []
        url = "https://www.espn.com/watch/schedule/_/type/upcoming"

        try:
            print(f"Fetching ESPN schedule from {url} using Selenium...")

            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            driver = webdriver.Chrome(options=chrome_options)

            try:
                driver.get(url)
                print("Waiting for page to load...")
                time.sleep(10)

                page_source = driver.page_source

                debug_html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'espn_debug.html')
                with open(debug_html_path, 'w', encoding='utf-8') as f:
                    f.write(page_source)
                print(f"Saved debug HTML to {debug_html_path}")

                if not HAS_BS4:
                    print("ERROR: BeautifulSoup4 not installed. Install with: pip install beautifulsoup4")
                    return programs

                soup = BeautifulSoup(page_source, 'html.parser')

                # ESPN uses table rows for schedule entries
                schedule_items = soup.find_all('tr', class_=re.compile(r'Table__TR'))
                # Filter to only data rows (not headers)
                schedule_items = [item for item in schedule_items if item.get('data-idx') is not None]

                print(f"Found {len(schedule_items)} schedule entries")

                # Debug: collect all unique logo alt texts
                unique_logos = set()
                for item in schedule_items:
                    logo_elem = item.find('td', class_=re.compile(r'Table__TD--logo'))
                    if logo_elem:
                        logo_img = logo_elem.find('img')
                        if logo_img:
                            logo_alt = logo_img.get('alt', '').lower()
                            if logo_alt:
                                unique_logos.add(logo_alt)

                if unique_logos:
                    print(f"Found logos for: {', '.join(sorted(unique_logos))}")

                current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                last_start_time = None

                for item in schedule_items:
                    try:
                        # Extract from table cells
                        time_elem = item.find('td', class_=re.compile(r'Table__TD--time'))
                        title_elem = item.find('td', class_=re.compile(r'Table__TD--name'))

                        # Get logo to determine channel
                        logo_elem = item.find('td', class_=re.compile(r'Table__TD--logo'))
                        logo_img = logo_elem.find('img') if logo_elem else None
                        logo_alt = logo_img.get('alt', '').lower() if logo_img else ''

                        time_text = time_elem.get_text(strip=True) if time_elem else None
                        title_text = title_elem.get_text(strip=True) if title_elem else None

                        if not time_text or not title_text:
                            continue

                        # Determine channel from logo
                        channel_name = ''
                        if 'espn2' in logo_alt:
                            channel_name = 'ESPN2'
                        elif 'espnu' in logo_alt:
                            channel_name = 'ESPNU'
                        elif 'espnews' in logo_alt:
                            channel_name = 'ESPNews'
                        elif 'espn+' in logo_alt or 'espnplus' in logo_alt:
                            channel_name = 'ESPN+'
                        elif 'deportes' in logo_alt or 'espndeportes' in logo_alt:
                            channel_name = 'ESPN Deportes'
                        elif logo_alt == 'sec' or 'sec network' in logo_alt or 'secnetwork' in logo_alt:
                            channel_name = 'SEC'
                        elif 'accextra' in logo_alt:
                            channel_name = 'ACCNX'
                        elif logo_alt == 'acc' or 'accn' in logo_alt or 'acc network' in logo_alt:
                            channel_name = 'ACCN'
                        elif 'espn1' in logo_alt or 'espn' in logo_alt:
                            channel_name = 'ESPN'
                        else:
                            channel_name = 'ESPN'

                        start_time = self.parse_time_string(time_text, current_date)

                        if start_time:
                            if last_start_time and start_time < last_start_time:
                                current_date += timedelta(days=1)
                                start_time = self.parse_time_string(time_text, current_date)

                            last_start_time = start_time
                            stop_time = start_time + timedelta(hours=2)

                            programs.append({
                                'start': start_time,
                                'stop': stop_time,
                                'title': title_text,
                                'desc': '',
                                'channel': channel_name
                            })

                    except Exception:
                        continue

                print(f"Successfully parsed {len(programs)} programs from ESPN.com")

            finally:
                driver.quit()

        except Exception as e:
            print(f"Error fetching from ESPN.com: {e}")
            import traceback
            traceback.print_exc()

        return programs

    def parse_time_string(self, time_str: str, base_date: datetime) -> datetime:
        """Parse time string to datetime (handles 12/24 hour formats)."""
        try:
            time_str = re.sub(r'\s*(ET|EST|EDT|PT|PST|PDT)\s*', '', time_str, flags=re.I).strip()

            for fmt in ['%I:%M %p', '%I:%M%p', '%I%p', '%H:%M', '%H%M']:
                try:
                    parsed_time = datetime.strptime(time_str, fmt)
                    return base_date.replace(hour=parsed_time.hour, minute=parsed_time.minute)
                except ValueError:
                    continue
        except Exception:
            pass

        return None

    def fetch_schedule(self) -> List[Dict]:
        """Fetch schedule from ESPN.com using Selenium."""
        print("Fetching from ESPN.com...")
        programs = self.fetch_schedule_espn_selenium()

        if not programs:
            print("\nERROR: Failed to fetch schedule from ESPN.com")
            print("Check: website availability, page structure, Chrome/ChromeDriver")

        return programs


class ChannelsXMLGenerator:
    """Generates and updates channels.xml file with channel metadata."""

    def __init__(self, filename='channels.xml'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)

        if not os.path.isabs(filename):
            self.filename = os.path.join(parent_dir, filename)
        else:
            self.filename = filename

        self.tree = None
        self.root = None
        self.load_or_create()

    def load_or_create(self):
        """Load existing channels.xml or create new one."""
        if os.path.exists(self.filename):
            try:
                self.tree = ET.parse(self.filename)
                self.root = self.tree.getroot()
            except Exception:
                self.create_new()
        else:
            self.create_new()

    def create_new(self):
        """Create new channels XML structure."""
        self.root = ET.Element('channels')
        self.tree = ET.ElementTree(self.root)

    def update_channel(self, channel_id: str, channel_name: str, logo_path: str = None, homepage: str = None):
        """Add or update a channel in channels.xml."""
        # Find existing channel
        for channel in self.root.findall('channel'):
            if channel.get('id') == channel_id:
                # Update existing
                name_elem = channel.find('name')
                if name_elem is not None:
                    name_elem.text = channel_name
                else:
                    name_elem = ET.SubElement(channel, 'name')
                    name_elem.text = channel_name

                if logo_path:
                    logo_elem = channel.find('logo')
                    if logo_elem is not None:
                        logo_elem.text = logo_path
                    else:
                        logo_elem = ET.SubElement(channel, 'logo')
                        logo_elem.text = logo_path

                if homepage:
                    home_elem = channel.find('homepage')
                    if home_elem is not None:
                        home_elem.text = homepage
                    else:
                        home_elem = ET.SubElement(channel, 'homepage')
                        home_elem.text = homepage
                return

        # Create new channel
        channel = ET.SubElement(self.root, 'channel')
        channel.set('id', channel_id)

        name_elem = ET.SubElement(channel, 'name')
        name_elem.text = channel_name

        if logo_path:
            logo_elem = ET.SubElement(channel, 'logo')
            logo_elem.text = logo_path

        if homepage:
            home_elem = ET.SubElement(channel, 'homepage')
            home_elem.text = homepage

    def prettify(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')

    def save(self):
        """Save the XML to file with pretty formatting."""
        try:
            xml_str = self.prettify(self.root)
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(xml_str)
        except Exception as e:
            print(f"Error saving {self.filename}: {e}")


class XMLTVGenerator:
    """Generates and updates XMLTV format guide.xml file."""

    def __init__(self, filename='guide.xml'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)

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
        self.root.set('generator-info-name', 'ESPN Schedule Scraper')
        self.root.set('generator-info-url', 'https://github.com/KevinKolb/CableGuide')
        self.tree = ET.ElementTree(self.root)
        print(f"Created new {self.filename}")

    def download_logo(self, logo_url: str, logo_filename: str) -> str:
        """Download logo to logos folder and return local path."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        logos_dir = os.path.join(parent_dir, 'logos')
        os.makedirs(logos_dir, exist_ok=True)

        logo_path = os.path.join(logos_dir, logo_filename)

        if not os.path.exists(logo_path):
            try:
                print(f"Downloading logo...")
                response = requests.get(logo_url, timeout=10)
                response.raise_for_status()
                with open(logo_path, 'wb') as f:
                    f.write(response.content)
                print(f"Saved logo to {logo_filename}")
            except Exception as e:
                print(f"Failed to download logo: {e}")
                return logo_url

        return f"logos/{logo_filename}"

    def ensure_channel(self, channel_id: str, channel_name: str, logo_url: str = None, logo_filename: str = None):
        """Ensure channel element exists in XML."""
        for channel in self.root.findall('channel'):
            if channel.get('id') == channel_id:
                return

        channel = ET.SubElement(self.root, 'channel')
        channel.set('id', channel_id)

        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = channel_name

        if logo_filename:
            if logo_url:
                icon_src = self.download_logo(logo_url, logo_filename)
            else:
                # Use existing local logo file
                icon_src = f"logos/{logo_filename}"
            icon = ET.SubElement(channel, 'icon')
            icon.set('src', icon_src)
        elif logo_url:
            icon = ET.SubElement(channel, 'icon')
            icon.set('src', logo_url)

        print(f"Added channel: {channel_name} ({channel_id})")

    def format_xmltv_time(self, dt: datetime) -> str:
        """Format datetime to XMLTV format: YYYYMMDDHHmmss +TZTZ."""
        offset = dt.strftime('%z') if dt.strftime('%z') else '+0000'
        return dt.strftime('%Y%m%d%H%M%S') + ' ' + offset

    def remove_channel_programs_in_range(self, channel_id: str, start_time: datetime, end_time: datetime):
        """Remove all programs for a channel within the specified date range."""
        programs_to_remove = []

        for programme in self.root.findall('programme'):
            if programme.get('channel') != channel_id:
                continue

            start_str = programme.get('start', '')
            try:
                prog_start = datetime.strptime(start_str[:14], '%Y%m%d%H%M%S')
                if start_time <= prog_start <= end_time:
                    programs_to_remove.append(programme)
            except:
                continue

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
        """Update guide with new programs (removes existing in date range first)."""
        if not programs:
            print("No programs to add")
            return

        self.ensure_channel(channel_id, channel_name, logo_url, logo_filename)

        start_time = min(p['start'] for p in programs)
        end_time = max(p['stop'] for p in programs)

        print(f"Updating {channel_name} schedule:")
        print(f"  From: {start_time.strftime('%Y-%m-%d %H:%M')}")
        print(f"  To:   {end_time.strftime('%Y-%m-%d %H:%M')}")

        self.remove_channel_programs_in_range(channel_id, start_time, end_time)

        for program in programs:
            self.add_program(channel_id, program)

        print(f"Added {len(programs)} programs")

    def sort_programs(self):
        """Sort all programs by channel ID, then by start time."""
        programs = list(self.root.findall('programme'))

        for prog in programs:
            self.root.remove(prog)

        programs.sort(key=lambda p: (p.get('channel', ''), p.get('start', '')))

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
            self.sort_programs()
            xml_str = self.prettify(self.root)

            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write(xml_str)

            size = os.path.getsize(self.filename)
            print(f"Saved {self.filename} ({size:,} bytes)")

        except Exception as e:
            print(f"Error saving {self.filename}: {e}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("ESPN TV Schedule Scraper")
    print("=" * 60)
    print()

    fetcher = ESPNScheduleFetcher()
    programs = fetcher.fetch_schedule()

    if not programs:
        print("Failed to fetch schedule data from ESPN.com")
        return 1

    # Group programs by channel
    channels = {}
    for program in programs:
        channel = program.get('channel', 'ESPN')
        if channel not in channels:
            channels[channel] = []
        channels[channel].append(program)

    print(f"\nFound {len(programs)} programs across {len(channels)} channels:")
    for channel, progs in channels.items():
        print(f"  {channel}: {len(progs)} programs")

    # Channel metadata - using local PNG logos
    channel_info = {
        'ESPN': {'id': 'espn.us', 'logo_url': None, 'logo_file': 'ESPN.svg', 'homepage': 'https://www.espn.com'},
        'ESPN2': {'id': 'espn2.us', 'logo_url': None, 'logo_file': 'espn2.png', 'homepage': 'https://www.espn.com/watch/espn2'},
        'ESPNU': {'id': 'espnu.us', 'logo_url': None, 'logo_file': 'espnu.png', 'homepage': 'https://www.espn.com/watch/espnu'},
        'ESPNews': {'id': 'espnews.us', 'logo_url': None, 'logo_file': 'espnews.png', 'homepage': 'https://www.espn.com/watch/espnews'},
        'ESPN+': {'id': 'espnplus.us', 'logo_url': None, 'logo_file': 'espn+.png', 'homepage': 'https://www.espn.com/espnplus'},
        'ESPN Deportes': {'id': 'espndeportes.us', 'logo_url': None, 'logo_file': 'espnd.png', 'homepage': 'https://www.espndeportes.com'},
        'SEC': {'id': 'secnetwork.us', 'logo_url': None, 'logo_file': 'sec.png', 'homepage': 'https://www.espn.com/watch/sec-network'},
        'ACCN': {'id': 'accn.us', 'logo_url': None, 'logo_file': 'accn.png', 'homepage': 'https://www.espn.com/watch/accn'},
        'ACCNX': {'id': 'accnx.us', 'logo_url': None, 'logo_file': 'accnx.png', 'homepage': 'https://www.espn.com/watch/accnx'},
    }

    # Update guide.xml
    xml_guide = XMLTVGenerator('guide.xml')

    for channel_name, progs in channels.items():
        info = channel_info.get(channel_name, {'id': channel_name.lower().replace(' ', '') + '.us', 'logo_url': None, 'logo_file': None})
        xml_guide.update_with_programs(
            channel_id=info['id'],
            channel_name=channel_name,
            programs=progs,
            logo_url=info['logo_url'],
            logo_filename=info['logo_file']
        )

    xml_guide.save()

    # Update channels.xml
    channels_xml = ChannelsXMLGenerator('channels.xml')
    for channel_name, progs in channels.items():
        info = channel_info.get(channel_name, {'id': channel_name.lower().replace(' ', '') + '.us', 'logo_file': None, 'homepage': None})
        if info.get('logo_file'):
            logo_path = f"logos/{info['logo_file']}"
        else:
            logo_path = None

        channels_xml.update_channel(
            channel_id=info['id'],
            channel_name=channel_name,
            logo_path=logo_path,
            homepage=info.get('homepage')
        )

    channels_xml.save()

    print()
    print("=" * 60)
    print("Done!")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
