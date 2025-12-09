# Ads Folder

This folder contains local ad images for the cable guide.

## How to Use

### In guide.xml, you can reference ads in two ways:

1. **URL-based images** (recommended):
   ```xml
   <ad url="https://www.mentos.com" image="https://example.com/mentos-ad.jpg" alt="Mentos - The Freshmaker">Mentos</ad>
   ```

2. **Local images** (place image files in this folder):
   ```xml
   <ad url="https://www.mentos.com" image="mentos-ad.jpg" alt="Mentos - The Freshmaker">Mentos</ad>
   ```

## Image Specifications

- **Recommended size**: 280px × 157px (16:9 aspect ratio)
- **Formats**: JPG, PNG, GIF
- **File naming**: Use lowercase with hyphens (e.g., `mentos-ad.jpg`)

## Example Structure

```
ads/
├── README.md
├── mentos-ad.jpg
├── pepsi-ad.png
└── nike-ad.jpg
```

## Current Ads in guide.xml

The current ads use URL-based images from the web:
- Mentos (YouTube thumbnail)
- Pepsi (Wikimedia Commons)
- Nike (Nike official site)

You can replace these with local images by downloading them to this folder and updating the `image` attribute in guide.xml.
