# Untappd Photo Downloader

A script to download user photos from Untappd.com using Selenium.

## ⚠️ Warning

This script is intended **for personal use only**. Use responsibly:

- Use only to save your own photos
- Respect the privacy of other users
- Follow Untappd's Terms of Service

## Features

- ✅ Automatic download of all user photos
- ✅ Download original (uncropped) photos
- ✅ Automatic "Show More" button clicking to load all photos
- ✅ Manual login to bypass CAPTCHA
- ✅ Skip already downloaded files
- ✅ Filter out beer and brewery logos

## Installation

### Prerequisites

- Python 3.7+
- Google Chrome browser

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `creds.txt` file in the project root:

```
your.email@example.com
yourpassword
```

**First line** - your Untappd email  
**Second line** - your password

2. In `scraper.py`, change `target_user` to the desired username:

```python
target_user = "your_username"  # Change as needed
```

## Usage

1. Run the script:

```bash
python scraper.py
```

2. Chrome browser will open

3. Manually log in to Untappd and pass CAPTCHA (if present)

4. After successful login, press **Enter** in the terminal

5. The script will automatically:
   - Load all photos (clicking "Show More")
   - Download original photos
   - Save them to `photos_{username}/`

## Settings

In the `main()` function of `scraper.py` you can modify:

- `target_user` - username to download photos from
- `delay=2.0` - delay between requests (in seconds)
- `output_dir` - folder to save photos

## Technical Details

The script uses:
- **Selenium WebDriver** - for browser automation and dynamic content loading
- **BeautifulSoup** - for HTML parsing and extracting `photoJSON`
- **Requests** - for downloading files
- **WebDriver Manager** - for automatic ChromeDriver installation

The script extracts original photo URLs from `<div id="photoJSON_*">`, which contains JSON with `photo.photo_img_og`.

## Project Structure

```
untappd/
├── creds.txt          # Credentials (don't commit!)
├── scraper.py         # Main script
├── requirements.txt   # Python dependencies
├── .gitignore         # Git ignore files
└── README.md          # Documentation
```

## License

MIT
