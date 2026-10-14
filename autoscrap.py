import argparse
from html.parser import HTMLParser
import random
import signal
import sqlite3
import time
from pathlib import Path

import requests


DATABASE_PATH = Path(__file__).resolve().parent / "11888_data.db"
RETRYABLE_STATUS_CODES = {403, 429, 500, 502, 503, 504}
REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}
REQUEST_TIMEOUT = (10, 30)
REQUEST_DELAY = (0.2, 0.6)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/149.0.0.0 Safari/537.36"
)

# Empty list means direct connection.
proxies = [
    # "http://user:pass@host:port",
]


class ContactHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.capture_name = False
        self.capture_location = False
        self.name_parts = []
        self.location_parts = []
        self.phones = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "main":
            self.in_main = True

        if not self.in_main:
            return

        if tag == "h1" and not self.name_parts:
            self.capture_name = True

        classes = set(attrs.get("class", "").split())
        if (
            tag == "span"
            and "tw-text-gray-secondary" in classes
            and not self.location_parts
        ):
            self.capture_location = True

        href = attrs.get("href", "")
        if tag == "a" and href.startswith("tel:"):
            phone = href.removeprefix("tel:").strip()
            if phone and phone not in self.phones:
                self.phones.append(phone)

    def handle_endtag(self, tag):
        if tag == "h1":
            self.capture_name = False
        elif tag == "span":
            self.capture_location = False
        elif tag == "main":
            self.in_main = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        if self.capture_name:
            self.name_parts.append(text)
        if self.capture_location:
            self.location_parts.append(text)


def clean_text(parts):
    return " ".join(" ".join(parts).split())


def parse_contact(html, page_id, page_url):
    parser = ContactHTMLParser()
    parser.feed(html)

    name = clean_text(parser.name_parts)
    if not name:
        return None

    return {
        "name": name,
        "location": clean_text(parser.location_parts) or "N/A",
        "phones": ", ".join(parser.phones) or "N/A",
        "page_url": page_url,
        "page": page_id,
    }


def connect_database(path, max_attempts=20):
    """Open and initialize SQLite, waiting if another worker has it locked."""
    for attempt in range(1, max_attempts + 1):
        conn = None
        try:
            conn = sqlite3.connect(path, timeout=60)
            conn.execute("PRAGMA busy_timeout=60000")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    location TEXT,
                    phones TEXT,
                    page_url TEXT,
                    page INTEGER
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_contacts_page ON contacts(page)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scrape_progress (
                    range_start INTEGER NOT NULL,
                    range_end INTEGER NOT NULL,
                    next_page INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (range_start, range_end)
                )
                """
            )
            conn.commit()
            return conn
        except sqlite3.OperationalError as exc:
            if conn is not None:
                conn.close()

            if "locked" not in str(exc).lower() or attempt == max_attempts:
                raise

            delay = min(0.25 * attempt, 5) + random.uniform(0, 0.5)
            print(
                f"[*] Database locked during startup; "
                f"retrying in {delay:.1f}s ({attempt}/{max_attempts})..."
            )
            time.sleep(delay)

    raise RuntimeError("Could not initialize the database")


def save_progress(cursor, args, next_page):
    cursor.execute(
        """
        INSERT INTO scrape_progress (
            range_start,
            range_end,
            next_page,
            updated_at
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(range_start, range_end) DO UPDATE SET
            next_page = excluded.next_page,
            updated_at = CURRENT_TIMESTAMP
        """,
        (args.start, args.end, next_page),
    )


def find_start_page(cursor, args):
    row = cursor.execute(
        """
        SELECT next_page
        FROM scrape_progress
        WHERE range_start = ? AND range_end = ?
        """,
        (args.start, args.end),
    ).fetchone()
    if row is not None:
        return min(max(row[0], args.start), args.end)

    row = cursor.execute(
        """
        SELECT MAX(page)
        FROM contacts
        WHERE page >= ? AND page < ?
        """,
        (args.start, args.end),
    ).fetchone()
    if row[0] is not None:
        return min(row[0] + 1, args.end)

    return args.start


def insert_contact(cursor, contact):
    cursor.execute(
        """
        INSERT INTO contacts (name, location, phones, page_url, page)
        SELECT ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM contacts WHERE page = ?
        )
        """,
        (
            contact["name"],
            contact["location"],
            contact["phones"],
            contact["page_url"],
            contact["page"],
            contact["page"],
        ),
    )
    return bool(cursor.rowcount)


def retry_delay(error_count, retry_after=None):
    if retry_after:
        try:
            return min(max(float(retry_after), 1), 60)
        except ValueError:
            pass

    base_delay = min(2 ** min(error_count, 5), 30)
    return base_delay + random.uniform(0, 1)


def request_proxy(proxy):
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Scrape a specific range of 11888 white-pages IDs."
    )
    parser.add_argument(
        "--start",
        type=int,
        required=True,
        help="First page ID (inclusive)",
    )
    parser.add_argument(
        "--end",
        type=int,
        required=True,
        help="Last page ID (exclusive)",
    )
    args = parser.parse_args()

    if args.start < 0:
        parser.error("--start must be zero or greater")
    if args.end <= args.start:
        parser.error("--end must be greater than --start")

    return args


def main():
    args = parse_arguments()
    conn = connect_database(DATABASE_PATH)
    cursor = conn.cursor()
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "el-GR,el;q=0.9,en;q=0.8",
        }
    )

    state = {"stop_requested": False}

    def request_stop(signum, _frame):
        state["stop_requested"] = True
        print(f"[*] Received signal {signum}; stopping after the current request...")

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    scrape_page = find_start_page(cursor, args)
    save_progress(cursor, args, scrape_page)
    conn.commit()

    proxy = random.choice(proxies) if proxies else None
    requests_with_current_ip = 0
    max_requests_per_ip = 100
    consecutive_errors = 0

    print(f"[*] Assigned range: {args.start:,} to {args.end - 1:,}")
    print(f"[*] Starting/resuming at page: {scrape_page:,}")
    print(f"[*] HTTP session. Proxy: {proxy or 'Direct IP'}")

    try:
        while scrape_page < args.end and not state["stop_requested"]:
            if proxies and requests_with_current_ip >= max_requests_per_ip:
                proxy = random.choice(proxies)
                requests_with_current_ip = 0
                session.cookies.clear()
                print(f"[*] Rotated proxy: {proxy}")

            url = f"https://www.11888.gr/white-pages/{scrape_page}/"
            print(f"Scraping page {scrape_page}: {url}")

            try:
                response = session.get(
                    url,
                    allow_redirects=False,
                    timeout=REQUEST_TIMEOUT,
                    proxies=request_proxy(proxy),
                )
                requests_with_current_ip += 1
            except requests.RequestException as exc:
                consecutive_errors += 1
                delay = retry_delay(consecutive_errors)
                print(
                    f"[!] Request error on page {scrape_page}: {exc}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES:
                consecutive_errors += 1
                delay = retry_delay(
                    consecutive_errors,
                    response.headers.get("Retry-After"),
                )
                print(
                    f"[!] HTTP {response.status_code} on page {scrape_page}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue

            consecutive_errors = 0

            if response.status_code in REDIRECT_STATUS_CODES:
                contact = None
                result = (
                    f"No contact on page {scrape_page} "
                    f"(HTTP {response.status_code}, "
                    f"location={response.headers.get('Location', 'N/A')})."
                )
            elif response.status_code == 200:
                contact = parse_contact(response.text, scrape_page, url)
                result = (
                    None
                    if contact
                    else f"No contact data in HTTP 200 page {scrape_page}."
                )
            else:
                contact = None
                result = (
                    f"No contact on page {scrape_page} "
                    f"(HTTP {response.status_code})."
                )

            try:
                inserted = insert_contact(cursor, contact) if contact else False
                next_page = scrape_page + 1
                save_progress(cursor, args, next_page)
                conn.commit()
            except sqlite3.OperationalError as exc:
                conn.rollback()
                delay = random.uniform(1, 3)
                print(
                    f"[!] SQLite error: {exc}. "
                    f"Retrying page {scrape_page} in {delay:.1f}s..."
                )
                time.sleep(delay)
                continue

            if contact and inserted:
                print(
                    f"Inserted: {contact['name']} | "
                    f"{contact['location']} | {contact['phones']}"
                )
            elif contact:
                print(f"Page {contact['page']} already exists; skipping insert.")
            else:
                print(result)

            scrape_page = next_page
            time.sleep(random.uniform(*REQUEST_DELAY))

        if state["stop_requested"]:
            print(f"[*] Worker stopped at page {scrape_page:,}. Progress saved.")
        else:
            print("Scraping complete!")
    finally:
        session.close()
        conn.close()


if __name__ == "__main__":
    main()
