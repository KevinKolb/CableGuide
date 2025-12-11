# CableGuide TODO

## Features

### Channel Metadata
- [ ] Denote which channels have commercials
  - Add a `hasCommercials` field to channels.xml
  - Update scrapers to include this metadata
  - Display commercial indicator in simpleview.html (maybe a small icon or text label)
  - Suggested implementation:
    - CNN: has commercials
    - ESPN family: has commercials
    - TNT: has commercials
    - ESPN+: no commercials (subscription)

## Future Enhancements
- [ ] Add more channel scrapers
- [ ] Implement program descriptions/details view
- [ ] Add search/filter functionality
- [ ] Cache schedule data
- [ ] Add refresh button to reload guide
