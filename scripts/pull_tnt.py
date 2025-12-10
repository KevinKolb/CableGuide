import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# URL for the TNT Drama TV schedule
url = 'https://www.tntdrama.com/tv-schedule'

# Set up Selenium with Chrome (headless mode for efficiency)
chrome_options = Options()
chrome_options.add_argument("--headless")  # Run in background
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

driver = webdriver.Chrome(options=chrome_options)

try:
    # Load the page
    driver.get(url)
    
    # Wait for the schedule to load (adjust timeout as needed)
    wait = WebDriverWait(driver, 10)
    # Wait for a common schedule container; adjust selector based on inspection
    # Common selectors: 'schedule-container', 'program-grid', '[data-schedule]', etc.
    # For now, wait for any div with 'schedule' in class or id
    schedule_container = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='schedule'], ul[class*='schedule'], section[id*='schedule']"))
    )
    
    # Get the page source after JS loads
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    # Now find the schedule items - adjust selector after inspecting the rendered HTML
    # Run without headless first to inspect: remove --headless, add time.sleep(5), then print(soup.prettify())
    # Hypothetical: items = soup.find_all('div', class_='schedule-item') or similar
    items = soup.find_all('div', class_=lambda x: x and ('program' in x.lower() or 'listing' in x.lower() or 'slot' in x.lower()))
    
    if not items:
        print("Could not find schedule items in rendered HTML. Inspect the page.")
        # For debugging: save HTML to file
        with open('debug_tnt.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("Saved rendered HTML to debug_tnt.html for inspection.")
        exit(1)
    
    print(f"Found {len(items)} schedule items.")
    
    # Create XML root (XMLTV format)
    root = ET.Element('tv')
    channel = ET.SubElement(root, 'channel')
    ET.SubElement(channel, 'display-name').text = 'TNT'
    
    # Get current date for start times (assuming today's date; adjust for full UTC)
    today = datetime.now().strftime('%Y%m%d')
    
    for idx, item in enumerate(items):
        # Extract data - update selectors based on actual structure
        # Common: time in <span class="time">, title in <h3 class="title">, etc.
        time_elem = item.find(['span', 'div', 'time'], class_=lambda x: x and any(kw in x.lower() for kw in ['time', 'hour', 'air']))
        time_text = time_elem.text.strip() if time_elem else f'Unknown{idx}'
        
        title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'a', 'span'], class_=lambda x: x and any(kw in x.lower() for kw in ['title', 'show', 'name']))
        title_text = title_elem.text.strip() if title_elem else 'Unknown Show'
        
        episode_elem = item.find('span', class_=lambda x: x and 'episode' in x.lower())
        episode_text = episode_elem.text.strip() if episode_elem else ''
        
        desc_elem = item.find(['p', 'div'], class_=lambda x: x and 'desc' in x.lower())
        desc_text = desc_elem.text.strip() if desc_elem else ''
        
        rating_elem = item.find('span', class_=lambda x: x and any(kw in x.lower() for kw in ['rating', 'tv-', 'mpaa']))
        rating_text = rating_elem.text.strip() if rating_elem else ''
        
        # Parse time to XMLTV format (e.g., 20251210090000 for 9:00 AM on Dec 10, 2025)
        # Simplified: assume 24h format, add today's date
        try:
            # Convert time_text like "9:00 pm" to 210000
            time_obj = datetime.strptime(time_text, '%I:%M %p')  # Adjust format as needed
            time_str = time_obj.strftime('%H%M%S')
            start_time = f"{today}{time_str}00 +0000"  # UTC placeholder
        except:
            start_time = f"{today}00000000 +0000"
        
        # Create programme element
        programme = ET.SubElement(root, 'programme', start=start_time, channel='TNT.id')  # Use channel id if known
        ET.SubElement(programme, 'title', lang='en').text = title_text
        if episode_text:
            ET.SubElement(programme, 'sub-title', lang='en').text = episode_text
        if desc_text:
            ET.SubElement(programme, 'desc', lang='en').text = desc_text
        if rating_text:
            rating = ET.SubElement(programme, 'rating')
            ET.SubElement(rating, 'value').text = rating_text
        
        print(f"Added: {time_text} - {title_text}")  # Debug print
    
    # Pretty print XML
    rough_string = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent='  ')
    
    # Output the XML (remove <?xml> if unwanted)
    print(pretty_xml)
    
    # Optionally save to file
    with open('tnt_schedule.xml', 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    print("Saved to tnt_schedule.xml")

finally:
    driver.quit()