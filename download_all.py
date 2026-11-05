
import re
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

COURSE_URL = "https://c2.etf.unsa.ba/course/view.php?id=220"
OUTPUT = Path("ETF_Predavanja")

IMAGE_SELECTOR = ".h5p-image-slide-image-holder img"
SLIDES_CONTAINER = ".h5p-image-slider-slides"
NEXT_BUTTON = (
    ".h5p-image-slider-right-button "
    ".h5p-image-slider-button-text"
)

MAX_SLIDES = 500


def safe_name(name):
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    return name.strip(" ._") or "Slideshow"


def download_image(context, url, output_path):
    response = context.request.get(url, timeout=60000)

    if not response.ok:
        print(f"  [!] HTTP {response.status}: {url}")
        return False

    try:
        image = Image.open(BytesIO(response.body()))
        image.load()
        image.save(output_path)
        return True
    except Exception as error:
        print(f"  [!] Invalid image: {error}")
        return False


def create_pdf(folder, name):
    files = sorted(
        f for f in folder.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        and f.stem.startswith("slide_"))
    
    if not files:
        files = sorted(folder.glob("slide_*.png"))

    if not files:
        print("  [!] No images available for PDF.")
        return

    images = []

    for file in files:
        with Image.open(file) as image:
            images.append(image.convert("RGB"))

    pdf_path = folder / f"{name}.pdf"

    images[0].save(
        pdf_path,
        "PDF",
        save_all=True,
        append_images=images[1:]
    )

    print(f"  [+] PDF created: {pdf_path}")


def process_slider(frame, context, folder, name):
    folder.mkdir(parents=True, exist_ok=True)

    container = frame.locator(SLIDES_CONTAINER).first
    container.wait_for(state="attached", timeout=15000)

    seen = set()
    downloaded = 0

    print(f"\n[*] Processing: {name}")

    # First, collect images already present in the HTML.
    urls = container.locator(IMAGE_SELECTOR).evaluate_all("""
        imgs => imgs.map(img =>
            img.currentSrc || img.src ||
            img.getAttribute('data-src')
        ).filter(Boolean)
    """)

    urls = list(dict.fromkeys(urls))

    for url in urls:
        if url in seen:
            continue

        seen.add(url)

        extension = Path(urlparse(url).path).suffix.lower()
        if extension not in (".jpg", ".jpeg", ".png", ".webp"):
            extension = ".jpg"

        output_path = folder / f"slide_{downloaded + 1:03d}{extension}"

        if download_image(context, url, output_path):
            downloaded += 1
            print(f"  [+] Slide {downloaded}")

    # If only one image was loaded, navigate through the slideshow.
    

    # Navigate through the slideshow by detecting new image URLs.
    next_button = frame.locator(NEXT_BUTTON).first

    def get_slide_urls():
        return container.locator(IMAGE_SELECTOR).evaluate_all("""
            imgs => imgs.map(img =>
                img.currentSrc || img.src ||
                img.getAttribute('data-src')
            ).filter(Boolean)
        """)

    for _ in range(MAX_SLIDES):

        if not next_button.is_visible():
            print("  [*] Next button hidden. End of slideshow.")
            break

        # Remember all currently loaded image URLs.
        previous_urls = get_slide_urls()

        # Advance one slide.
        next_button.click()

        # Wait until H5P loads a new image.
        try:
            frame.wait_for_function(
                """arg => {
                    const imgs = document.querySelectorAll(arg.selector);

                    const urls = Array.from(imgs).map(img =>
                        img.currentSrc || img.src ||
                        img.getAttribute('data-src')
                    ).filter(Boolean);

                    return urls.some(url =>
                        !arg.previous.includes(url)
                    );
                }""",
                arg={
                    "selector": IMAGE_SELECTOR,
                    "previous": previous_urls
                },
                timeout=8000
            )

        except Exception:
            print("  [*] No new image detected. End of slideshow.")
            break

        # Find newly loaded images.
        current_urls = get_slide_urls()

        new_urls = [
            url for url in current_urls
            if url not in seen
        ]

        # Download all newly discovered images.
        for url in new_urls:

            seen.add(url)

            extension = Path(urlparse(url).path).suffix.lower()

            if extension not in (".jpg", ".jpeg", ".png", ".webp"):
                extension = ".jpg"

            output_path = folder / f"slide_{downloaded + 1:03d}{extension}"

            if download_image(context, url, output_path):
                downloaded += 1
                print(f"  [+] Slide {downloaded}")

    print(f"  [*] Total downloaded: {downloaded}")

    # Assemble all downloaded slide images into a PDF.
    create_pdf(folder, name)


def main():
    OUTPUT.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        page = context.new_page()

        print("[*] Opening ETF Moodle...")
        page.goto(COURSE_URL, wait_until="domcontentloaded")

        input(
            "\nLog in to Moodle if necessary.\n"
            "Make sure the course page is open, then press ENTER..."
        )

        page.goto(COURSE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        # H5P content can be embedded in an iframe.
        frames = page.frames

        slideshow_count = 0

        for frame in frames:
            try:
                sliders = frame.locator(SLIDES_CONTAINER)
                count = sliders.count()

                for index in range(count):
                    slideshow_count += 1

                    name = f"Slideshow_{slideshow_count:02d}"

                    process_slider(
                        frame,
                        context,
                        OUTPUT / name,
                        name
                    )

            except Exception as error:
                print(f"[!] Frame skipped: {error}")

        print(f"\n[+] Found {slideshow_count} slideshow(s).")
        print(f"[+] Output: {OUTPUT.resolve()}")

        browser.close()


if __name__ == "__main__":
    main()
