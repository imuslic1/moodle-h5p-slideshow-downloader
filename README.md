# Moodle H5P Slideshow Downloader

A Python utility for downloading the individual slide images from **H5P Image Slider** activities embedded in a Moodle course. It can keep the original images, assemble them into PDFs, and run OCR so the resulting PDFs are searchable. It can also export the recognized text into `.txt` files.

The scripts use Playwright to open Moodle in Chromium. You sign in through the normal browser window; the scripts do not ask you to put your Moodle password in the source code.

> **Important:** This project is designed for Moodle courses that you are authorized to access. Follow your institution's rules and the course's copyright conditions. Do not publish or redistribute downloaded lecture slides unless you have permission. The GitHub repository should contain the downloader code, not private course content, images, PDFs, browser profiles, or credentials.

## Features

- Opens a Moodle course page in Chromium using Playwright.
- Supports H5P Image Slider markup matching the selectors used in the scripts.
- Downloads slide image files from Moodle's image URLs rather than taking screenshots.
- Saves slides in numbered order (`slide_001.jpg`, `slide_002.jpg`, etc.).
- Creates one PDF per slideshow.
- Adds an OCR text layer to PDFs, making recognized text selectable and searchable.
- Writes a separate text transcript for each slideshow.
- Provides two modes: download all detected slideshows, or select one likely-newest slideshow.

## Scripts

Put the two Python scripts in the repository root with these names:

| File | Purpose |
|---|---|
| `download_all.py` | Scans the course page and processes every H5P Image Slider it finds. |
| `download_latest.py` | Selects one slideshow using the highest H5P content ID found in its image URLs, then processes only that slideshow. |

If your existing all-slideshows script is still named `script.py`, rename it to `download_all.py` or change the command in this README.

### How the “latest” mode chooses a slideshow

The current `download_latest.py` implementation extracts the number in URLs shaped like:

```text
/pluginfile.php/1/core_h5p/content/125/images/Slide1.JPG
```

It selects the slideshow with the **highest H5P content ID** among the sliders discovered on the course page. Moodle content IDs often increase as new content is created, but this is a heuristic—not a guaranteed upload timestamp. If the professor edits an existing H5P activity, its ID may stay the same. If the IDs do not identify the newest activity, update the selection logic to use Moodle's activity metadata or modification time instead.

The current script also skips a selected slideshow when its output PDF already exists. Delete that slideshow's output folder (or at least its PDF) to force another download. Be aware that deleting only the PDF may leave old images behind; deleting the whole output folder is the cleanest option.

## Requirements

- Windows, macOS, or Linux.
- Python 3.10 or newer is recommended.
- Access to the Moodle course and permission to download its materials.
- Tesseract OCR installed separately from Python.
- An internet connection.

Python packages:

- Playwright
- Pillow
- PyMuPDF
- pytesseract

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
cd YOUR-REPOSITORY
```

Replace the URL with the URL of your GitHub repository.

### 2. Create and activate a virtual environment

**Windows PowerShell:**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt:**

```bat
py -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies and Chromium

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
```

### 4. Install Tesseract OCR

Tesseract is a separate system application; installing `pytesseract` with pip is not enough.

#### Installing Tesseract OCR
Tesseract must be installed separately from the Python
dependencies.

Choose the installation method for your operating system:

### Windows

The recommended method is the UB Mannheim installer or Windows Package Manager.

**Option 1 — Windows Package Manager (winget):**

```powershell
winget install UB-Mannheim.TesseractOCR
```

**Option 2 — Manual installation:**

1. Download the latest installer from the
   [UB Mannheim Tesseract builds](https://github.com/UB-Mannheim/tesseract/wiki).
2. Run the installer and select the language data you need.
3. Add the installation directory to your system PATH:

   ```text
   C:\Program Files\Tesseract-OCR
   ```

4. Restart your terminal.

### macOS

Install using [Homebrew](https://brew.sh/):

```bash
brew install tesseract
brew install tesseract-lang
```

The second command installs additional language data.

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install tesseract-ocr
```

To install all available language packages:

```bash
sudo apt install tesseract-ocr-all
```

### Fedora

```bash
sudo dnf install tesseract tesseract-langpack-eng
```

### Arch Linux / Manjaro

```bash
sudo pacman -S tesseract tesseract-data-eng
```

### Conda (cross-platform alternative)

If you are using Conda:

```bash
conda install -c conda-forge tesseract
```

### Verifying the installation

After installation, open a terminal and execute:

```bash
tesseract --version
tesseract --list-langs
```

The first command should display the installed Tesseract version.
The second lists the available OCR languages.

After installing Tesseract for your operating system, make sure its executable is on your `PATH`. On Windows, the executable is commonly located at:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

If it is not on `PATH`, set the path near the top of both scripts:

```python
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)
```

The scripts currently use `OCR_LANG = "eng"`. For Bosnian and English OCR, install the Tesseract language data for both `bos` and `eng`, then set:

```python
OCR_LANG = "bos+eng"
```

The language data must be installed in Tesseract's `tessdata` directory. If Tesseract reports that a language is unavailable, verify that the corresponding `.traineddata` file is installed.

## Configuration

At the top of each script, update the course URL and output directory as needed:

```python
COURSE_URL = "https://your-moodle.example/course/view.php?id=123"
OUTPUT = Path("Moodle_Slides")
```

The CSS selectors are specific to the H5P Image Slider layout currently used by the target course:

```python
IMAGE_SELECTOR = ".h5p-image-slide-image-holder img"
SLIDES_CONTAINER = ".h5p-image-slider-slides"
NEXT_BUTTON = ".h5p-image-slider-right-button .h5p-image-slider-button-text"
```

If another Moodle site uses a different H5P version, theme, or viewer, these selectors and possibly the navigation logic may need to be adjusted.

## Usage

Run one of the scripts from the repository directory.

### Download every detected slideshow

```bash
python download_all.py
```

### Download only the selected latest slideshow

```bash
python download_latest.py
```

A Chromium window opens. Sign in to Moodle normally if prompted. Once signed in, return to the terminal and press **Enter** when asked. Keep the browser open until the script finishes.

The scripts do not bypass Moodle authentication or course permissions. They use the browser session created by Playwright to access the pages and image URLs.

## Output

The default output directory is `ETF_Predavanja/` (or the directory configured in the script). Each slideshow gets its own folder, for example:

```text
ETF_Predavanja/
└── Latest_125/
    ├── slide_001.jpg
    ├── slide_002.jpg
    ├── slide_003.jpg
    ├── ...
    ├── Latest_125.pdf
    └── Latest_125.txt
```

- `slide_*.jpg` / `slide_*.png` / `slide_*.webp`: downloaded slide images.
- `*.pdf`: PDF with the slide images and an invisible OCR text layer.
- `*.txt`: OCR transcript, separated by slide number.

The OCR output is approximate. It may make mistakes with equations, mathematical symbols, small text, unusual fonts, multi-column layouts, and text embedded in diagrams. Check the original slide image when accuracy matters.

## Troubleshooting

### `TesseractNotFoundError` or Tesseract executable not found

Install Tesseract and add its executable to `PATH`, or set `pytesseract.pytesseract.tesseract_cmd` in the scripts.

### Tesseract says a language is not available

Install the requested language data (for example, `eng` or `bos`) into Tesseract's `tessdata` directory. Ensure `OCR_LANG` matches the installed language codes.

### No H5P slideshows are found

Make sure the course page has loaded and the slideshow activities are embedded in that page. The scripts scan the current course page and its frames; they do not automatically crawl every Moodle course section or visit every activity link. The H5P viewer's HTML structure may also have changed.

### Only some slides are downloaded

The scripts detect newly loaded image URLs after clicking the viewer's Next button. If the Moodle/H5P viewer changes its loading behavior, inspect the page with browser developer tools and update the selectors or wait condition. Do not assume that a run completed successfully unless the slide count and final PDF have been checked.

### The latest script selects the wrong presentation

The highest content ID is only a heuristic. Compare the IDs printed by the script with the course's actual newest activity. If the professor updates an existing activity, its content ID may not change.

### A slideshow is not downloaded again

The latest script skips a slideshow if its PDF already exists. Delete that slideshow's output folder to force a clean download.

## Suggested repository layout

```text
moodle-h5p-slideshow-downloader/
├── README.md
├── download_all.py
├── download_latest.py
├── requirements.txt
├── .gitignore
└── LICENSE                 # optional; choose a license before publishing
```

Do **not** commit:

- `.venv/` or other virtual environments;
- `ETF_Predavanja/` or any downloaded course files;
- PDFs, slide images, OCR transcripts, or other course materials;
- browser profiles, session data, cookies, passwords, or access tokens;
- Python cache files such as `__pycache__/`.