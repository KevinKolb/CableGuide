# Cable Guide

A retro-styled cable TV guide web application with infinite auto-scrolling and interactive features.

![Cable Guide Screenshot](screenshot.png)

## Features

- 📺 **Retro TV Guide Design** - Nostalgic cable guide interface with scanline effects
- 🔄 **Infinite Auto-Scroll** - Seamless infinite loop scrolling with no visible jump
- 🖱️ **Click & Drag** - Manual scrolling with mouse drag functionality
- 🎯 **Channel Filtering** - Toggle channels on/off with checkboxes
- 📊 **Dynamic Channel Count** - Real-time update of visible channels
- 🎬 **Clickable Ads** - Support for both URL-based and local ad images
- 🔍 **Fullscreen Mode** - Expand to fullscreen for immersive viewing
- ⏰ **Live Clock** - Real-time clock display in the corner
- 📱 **Responsive Design** - Adapts to different screen sizes

## Getting Started

### Prerequisites

- A modern web browser (Chrome, Firefox, Safari, Edge)
- A web server (for local development, you can use Python's built-in server or VS Code Live Server)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CableGuide.git
cd CableGuide
```

2. Get a TV listings API key:
   - Sign up at [TV Media API](https://tvmedia.ca/) for a free API key
   - Copy `.env.example` to create your own configuration
   - Add your API key to `index.html` (line 12):
   ```javascript
   const API_KEY = "your_api_key_here";
   ```

3. Run a local web server:

   **Option 1: Python**
   ```bash
   python -m http.server 8000
   ```

   **Option 2: VS Code Live Server**
   - Install the Live Server extension
   - Right-click on `index.html` and select "Open with Live Server"

4. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## Project Structure

```
CableGuide/
├── index.html          # Main HTML file with embedded JavaScript
├── style.css           # All styling and layout
├── guide.xml           # Sample XML data for channels and ads
├── ads/                # Directory for local ad images
│   ├── README.md       # Instructions for ad management
│   └── [ad images]     # Place your ad images here
└── README.md           # This file
```

## Configuration

### Setting Your Location

Edit the ZIP code in `index.html` (line 73):
```javascript
const zip = "70130"; // Change to your ZIP code
```

### Adding Custom Channels

Add custom channels to `guide.xml`:
```xml
<channel>
  <number>CNN</number>
  <name>CNN</name>
  <shows>
    <show start="8:00 AM" duration="60" description="Morning news">CNN This Morning</show>
  </shows>
</channel>
```

### Adding Ads

1. **Using URL-based ads:**
```xml
<ads>
  <ad url="https://example.com" image="https://example.com/ad.jpg" alt="Ad Description">Brand Name</ad>
</ads>
```

2. **Using local ad images:**
   - Place image in `ads/` folder
   - Reference in XML:
```xml
<ads>
  <ad url="https://example.com" image="local-ad.jpg" alt="Ad Description">Brand Name</ad>
</ads>
```

**Recommended ad dimensions:** 280px × 157px (16:9 aspect ratio)

### Adjusting Scroll Speed

Modify the scroll speed in `index.html` (line 287):
```javascript
let autoScrollSpeed = 0.5; // pixels per frame (adjust as needed)
```

## Features Breakdown

### Auto-Scroll with Infinite Loop
The guide automatically scrolls vertically using `requestAnimationFrame`. Content is duplicated and seamlessly loops back to the beginning.

### Click-and-Drag Navigation
Click and hold on the guide to manually scroll. The infinite loop is maintained during dragging.

### Channel Filters
Use the collapsible channel panel at the top to toggle specific channels on/off. The visible channel count updates dynamically.

### Fullscreen Mode
Click the fullscreen button (⛶) in the top-left corner to expand the guide. Press ESC to exit.

### Random Ad Display
On each page load, one random ad is selected from the available ads in `guide.xml`.

## Browser Support

- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

## Customization

### Colors and Theme
All colors are defined in `style.css`. Look for CSS custom properties and gradient definitions to customize the retro color scheme.

### Layout Dimensions
- Screen height: `.screen { height: 900px; }` (line 34)
- Guide container height: `.guide-container { height: 770px; }` (line 130)
- Max width: `.tv-container { max-width: 1400px; }` (line 25)

## API Information

This project uses the [TV Media API](https://tvmedia.ca/) to fetch live TV listings. The free tier includes:
- Channel lineups by ZIP code
- Program schedules
- Show descriptions and metadata

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Retro TV guide design inspired by 1990s cable TV interfaces
- Built with vanilla JavaScript for simplicity and performance
- TV listings powered by [TV Media API](https://tvmedia.ca/)

## Contact

Kevin Kolb - [kevinmkolb@gmail.com](mailto:kevinmkolb@gmail.com)

Project Link: [https://github.com/yourusername/CableGuide](https://github.com/yourusername/CableGuide)

---

**Vibe Coded by Kevin Kolb**
