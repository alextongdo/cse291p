# Layout Scraper

Capture geometric layout of HTML elements across multiple viewport sizes using Playwright.

## Setup

```bash
# Install dependencies
pip install playwright

# Install browser binaries
playwright install chromium
```

## Usage

```bash
cd layout_scraper

# Run with default config
python main.py

# Run with custom config
python main.py --config my_sites.json --output-dir ./output
```

## Configuration

Edit `config.json` to specify sites and selectors:

```json
{
  "sites": [
    {
      "url": "https://example.com",
      "name": "example_site",
      "selectors": ["body", "header", "#main", ".sidebar"]
    }
  ],
  "viewports": {
    "wide": [
      {"width": 1920, "height": 1080, "label": "desktop_large"}
    ],
    "thin": [
      {"width": 375, "height": 812, "label": "iphone_x"}
    ]
  },
  "settings": {
    "wait_after_resize_ms": 1000,
    "timeout_ms": 30000
  }
}
```

## Output

Two output formats per site:

1. **`{name}_raw.json`** - Raw data grouped by viewport
2. **`{name}_mockdown.json`** - Mockdown-compatible format with examples

### Mockdown Format

```json
{
  "examples": [
    {
      "name": "root",
      "rect": [0, 0, 1920, 1080],
      "children": [
        {"name": "header", "rect": [0, 0, 1920, 80], "children": []},
        {"name": "main", "rect": [0, 80, 1920, 1000], "children": []}
      ]
    }
  ]
}
```

## Viewports

Default viewports capture wide vs thin layouts:

| Category | Label | Size |
|----------|-------|------|
| Wide | desktop_large | 1920x1080 |
| Wide | desktop_medium | 1366x768 |
| Wide | tablet_landscape | 1024x768 |
| Thin | iphone_x | 375x812 |
| Thin | iphone_xr | 414x896 |
| Thin | android_small | 360x800 |

