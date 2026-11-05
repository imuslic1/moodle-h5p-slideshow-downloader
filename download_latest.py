import re
import pytesseract
import fitz

from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

# Optional: specify the Tesseract executable manually.
# Uncomment if Tesseract is not available through PATH.
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
)

COURSE_URL = "https://c2.etf.unsa.ba/course/view.php?id=220"
OUTPUT = Path("ETF_Predavanja")

IMAGE_SELECTOR = ".h5p-image-slide-image-holder img"
SLIDES_CONTAINER = ".h5p-image-slider-slides"

NEXT_BUTTON = (
    ".h5p-image-slider-right-button "
    ".h5p-image-slider-button-text"
)

MAX_SLIDES = 500

# OCR language:
OCR_LANG = "bos+eng"


def get_slide_urls(container):
    return container.locator(IMAGE_SELECTOR).evaluate_all("""
        imgs => imgs.map(img =>
            img.currentSrc || img.src ||
            img.getAttribute('data-src')
        ).filter(Boolean)
    """)


def get_content_id(urls):
    """Extract H5P content ID from Moodle pluginfile URLs."""
    ids = []

    for url in urls:
        match = re.search(r"/core_h5p/content/(\d+)/", url)

        if match:
            ids.append(int(match.group(1)))

    return max(ids) if ids else None


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
    # Find all downloaded slide images in their correct order.
    files = sorted(
        f for f in folder.iterdir()
        if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        and f.stem.startswith("slide_")
    )

    if not files:
        print("  [!] No images available for PDF.")
        return

    # Check that Tesseract is installed and accessible.
    try:
        pytesseract.get_tesseract_version()
    except Exception as error:
        print("  [!] Tesseract OCR is not installed or not in PATH.")
        print(f"  [!] Details: {error}")
        return

    pdf = fitz.open()

    print(f"\n[*] Starting OCR on {len(files)} slides...")

    # Process each slide individually.
    for index, file in enumerate(files, start=1):
        print(f"  [OCR] Processing slide {index}/{len(files)}...")

        try:
            with Image.open(file) as image:
                image = image.convert("RGB")

                # Generate a PDF page containing the original image
                # and an invisible, searchable OCR text layer.
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    image,
                    extension="pdf",
                    lang=OCR_LANG,
                    config="--psm 3"
                )

            # Add the OCR-generated page to the final PDF.
            slide_pdf = fitz.open(
                stream=pdf_bytes,
                filetype="pdf"
            )

            pdf.insert_pdf(slide_pdf)
            slide_pdf.close()

        except Exception as error:
            print(f"  [!] OCR failed on {file.name}: {error}")

    if pdf.page_count == 0:
        print("  [!] No PDF pages were successfully generated.")
        pdf.close()
        return

    # Save searchable PDF.
    pdf_path = folder / f"{name}.pdf"

    pdf.save(
        str(pdf_path),
        garbage=4,
        deflate=True
    )

    # Extract recognized text from the searchable PDF.
    text_content = []

    for index, page in enumerate(pdf, start=1):
        text = page.get_text("text", sort=True)

        text_content.append(
            f"\n{'=' * 50}\n"
            f"SLIDE {index}\n"
            f"{'=' * 50}\n\n"
            f"{text}"
        )

    pdf.close()

    # Save separate OCR transcript.
    txt_path = folder / f"{name}.txt"

    txt_path.write_text(
        "\n".join(text_content),
        encoding="utf-8"
    )

    print(f"\n  [+] Searchable PDF created: {pdf_path}")
    print(f"  [+] OCR transcript created: {txt_path}")



def process_slider(frame, context, slider_index, folder, name):
    folder.mkdir(parents=True, exist_ok=True)

    container = frame.locator(SLIDES_CONTAINER).nth(slider_index)
    container.wait_for(state="attached", timeout=15000)

    next_button = frame.locator(NEXT_BUTTON).nth(slider_index)

    seen = set()
    downloaded = 0

    print(f"\n[*] Downloading: {name}")

    # Download initially loaded slides.
    urls = list(dict.fromkeys(get_slide_urls(container)))

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

    # Navigate through the rest of the slideshow.
    for _ in range(MAX_SLIDES):

        if not next_button.is_visible():
            print("  [*] Next button hidden. End of slideshow.")
            break

        previous_urls = get_slide_urls(container)

        next_button.click()

        try:
            frame.wait_for_function(
                """arg => {
                    const containers = document.querySelectorAll(
                        arg.containerSelector
                    );

                    const container = containers[arg.containerIndex];

                    if (!container) return false;

                    const imgs = container.querySelectorAll(
                        arg.imageSelector
                    );

                    const urls = Array.from(imgs).map(img =>
                        img.currentSrc || img.src ||
                        img.getAttribute('data-src')
                    ).filter(Boolean);

                    return urls.some(url =>
                        !arg.previous.includes(url)
                    );
                }""",
                arg={
                    "containerSelector": SLIDES_CONTAINER,
                    "containerIndex": slider_index,
                    "imageSelector": IMAGE_SELECTOR,
                    "previous": previous_urls
                },
                timeout=8000
            )

        except Exception:
            print("  [*] No new image detected. End of slideshow.")
            break

        current_urls = get_slide_urls(container)

        new_urls = [
            url for url in current_urls
            if url not in seen
        ]

        for url in new_urls:
            seen.add(url)

            extension = Path(urlparse(url).path).suffix.lower()

            if extension not in (".jpg", ".jpeg", ".png", ".webp"):
                extension = ".jpg"

            output_path = folder / f"slide_{downloaded + 1:03d}{extension}"

            if download_image(context, url, output_path):
                downloaded += 1
                print(f"  [+] Slide {downloaded}")

    print(f"\n[+] Total slides downloaded: {downloaded}")

    # Generate PDF.
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

        print("\n[*] Searching for H5P slideshows...")

        candidates = []

        # Discover all slideshows across Moodle frames.
        for frame in page.frames:
            try:
                sliders = frame.locator(SLIDES_CONTAINER)
                count = sliders.count()

                for index in range(count):
                    container = sliders.nth(index)
                    urls = get_slide_urls(container)

                    content_id = get_content_id(urls)

                    candidates.append({
                        "frame": frame,
                        "index": index,
                        "content_id": content_id,
                        "image_count": len(urls)
                    })

            except Exception as error:
                print(f"[!] Frame skipped: {error}")

        if not candidates:
            print("[!] No H5P slideshows found.")
            browser.close()
            return

        # Display discovered presentations.
        print("\n[*] Discovered slideshows:")

        for index, item in enumerate(candidates, 1):
            print(
                f"  {index}. Content ID: "
                f"{item['content_id'] or 'Unknown'}"
                f" | Loaded images: {item['image_count']}"
            )

        # Select the slideshow with the highest H5P content ID.
        identified = [
            item for item in candidates
            if item["content_id"] is not None
        ]

        if identified:
            latest = max(
                identified,
                key=lambda item: item["content_id"]
            )

            content_id = latest["content_id"]

            print(
                f"\n[+] Latest slideshow identified: "
                f"H5P content ID {content_id}"
            )

            name = f"Latest_{content_id}"

        else:
            # Fallback: last slideshow in Moodle frame order.
            latest = candidates[-1]

            print(
                "\n[!] Could not determine H5P content IDs."
                "\n[!] Falling back to the last discovered slideshow."
            )

            name = "Latest_Unknown"

        # Use a separate folder for each H5P content ID.
        folder = OUTPUT / name
        pdf_path = folder / f"{name}.pdf"

        # Avoid downloading the same presentation again.
        if pdf_path.exists():
            print(f"\n[+] Already downloaded: {pdf_path}")
            browser.close()
            return

        # Remove leftover images from an incomplete previous run.
        if folder.exists():
            for file in folder.glob("slide_*"):
                file.unlink()

        process_slider(
            latest["frame"],
            context,
            latest["index"],
            folder,
            name
        )

        print("\n===================================")
        print("[+] Finished!")
        print(f"[+] Selected slideshow: {name}")
        print(f"[+] Output folder: {folder.resolve()}")
        print("===================================")

        browser.close()


if __name__ == "__main__":
    main()
