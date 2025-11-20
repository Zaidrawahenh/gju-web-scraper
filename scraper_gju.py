import time
import csv
import uuid
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

OUTPUT_FILE = "gju_all_pages.csv"
INPUT_CSV = "urls.csv"


def parse_pages_from_csv(csv_file):
    df = pd.read_csv(csv_file)
    pages = []
    for _, row in df.iterrows():
        pages.append((row["category"], row["url"]))
    return pages


def get_department(driver, fallback_category: str) -> str:
    try:
        h1 = driver.find_element(By.TAG_NAME, "h1")
        text = h1.text.strip()
        if text:
            return text
    except Exception:
        pass

    try:
        title = driver.title.strip()
        if title:
            return title
    except Exception:
        pass

    return fallback_category


def extract_text(driver) -> str:
    selectors = [
        "#content",
        ".region-content",
        ".content",
        ".node",
        ".field",
        ".view-content",
        ".main-content",
        ".col-md-9",
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            tx = el.text.strip()
            if len(tx.split()) > 40:
                return tx
        except Exception:
            pass

    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text.strip()
        return body_text
    except Exception:
        return ""


def make_chunks_exact(text: str, chunk_size: int = 260, overlap: int = 50):
    words = text.split()
    n = len(words)
    chunks = []

    if n == 0:
        return chunks

    step = chunk_size - overlap
    start = 0

    while True:
        end = start + chunk_size
        if end >= n:
            chunk_words = words[start:n]
            if chunk_words:
                chunks.append(" ".join(chunk_words))
            break
        else:
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))

        start += step

    return chunks


def scrape():
    print("⚙️  Starting scraper...")

    pages = parse_pages_from_csv(INPUT_CSV)
    print(f"🔢 Total pages to scrape: {len(pages)}")

    if not pages:
        print(" No pages found in CSV.")
        return

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    rows = []

    for idx, (category, url) in enumerate(pages, start=1):
        print(f"\n[{idx}/{len(pages)}] Category: {category} | URL: {url}")
        try:
            driver.get(url)
            time.sleep(3)

            department = get_department(driver, fallback_category=category)
            print(f"   [*] Department: {department}")

            text = extract_text(driver)
            words_count = len(text.split())
            print(f"   [*] Total words in page: {words_count}")

            if words_count < 10:
                print("   [!] Very short or empty text. Skipping.")
                continue

            chunks = make_chunks_exact(text, chunk_size=260, overlap=50)
            print(f"   [*] Created {len(chunks)} chunks")

            title = url.rstrip("/").split("/")[-1] or department

            for ck in chunks:
                rows.append({
                    "primary_key": str(uuid.uuid4()),
                    "title": title,
                    "sourcetype": "webpage",
                    "url": url,
                    "section": category,
                    "language": "English",
                    "department": department,
                    "last_updated": "",
                    "chunk": ck
                })

        except Exception as e:
            print(f"    Error scraping {url}: {e}")

    driver.quit()

    if not rows:
        print("\n No rows scraped, NOT creating CSV.")
        return

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n🎉 DONE! Saved {len(rows)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    print("👉 Script started (main.py)")
    scrape()
    print("👉 Script finished")
