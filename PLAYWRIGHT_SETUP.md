# Playwright Setup Guide

## Installation

After installing the Python package, you need to install the Playwright browsers:

```bash
# Install Python package (already in requirements.txt)
pip install playwright

# Install Playwright browsers
playwright install chromium
```

Or install all browsers:
```bash
playwright install
```

## What Changed

The scrapers now use Playwright to:
- Render JavaScript-rendered pages
- Wait for content to load
- Extract case information from fully rendered pages

## Usage

The scrapers will automatically use Playwright when `use_playwright=True` is set (which is now the default for Mass.gov scrapers).

Run the collection as before:
```bash
python main.py
```

## Troubleshooting

### "Playwright not installed" error
- Make sure you ran: `pip install playwright`
- Then run: `playwright install chromium`

### Browser download issues
- Playwright needs to download browser binaries (~200MB)
- Ensure you have internet connection and sufficient disk space
- If download fails, try: `playwright install --with-deps chromium`

### Slow performance
- Playwright is slower than requests because it renders full pages
- This is necessary for JavaScript-rendered content
- Consider running with smaller date ranges for testing
