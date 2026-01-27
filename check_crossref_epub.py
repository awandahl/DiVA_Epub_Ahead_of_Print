#!/usr/bin/env python3
import csv
import time
import requests
from tqdm import tqdm  # pip install tqdm
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path

# ---- CONFIG ----

DIVA_URL = (
    "https://kth.diva-portal.org/smash/export.jsf"
    "?format=csv"
    "&addFilename=true"
    "&aq=[[]]"
    "&aqe=[]"
    "&aq2=[[{\"publicationStatus\":\"aheadofprint\"}]]"
    "&onlyFullText=false"
    "&noOfRows=9999"
    "&sortOrder=title_sort_asc"
    "&sortOrder2=title_sort_asc"
    "&csvType=publication"
    "&fl=PID,DOI"
)

INPUT_CSV = "dois_input.csv"      # downloaded from Diva
OUTPUT_CSV = "dois_with_status.csv"
DOI_FIELD = "DOI"                 # must match Diva header
SLEEP_SECONDS = 1.0               # be nice to Crossref

CROSSREF_API_URL = "https://api.crossref.org/works/{}"
USER_AGENT = "kth-epub-checker/1.0 (mailto:aw@kth.se)"

# SMTP for golonka.se (tested successfully)
SMTP_HOST = "shared17.arvixe.com"
SMTP_PORT = 465                  # SSL/TLS
SMTP_USER = "anders@golonka.se"
SMTP_PASS = "************"           # <-- your real password

FROM_ADDR = "anders@golonka.se"
TO_ADDRS = [
    "biblioteket@kth.se",
    "aw@kth.se",
    "michaea@kth.se",
]
SUBJECT = "Läggs i VS KTHB Publicering/Category=DiVA:  Weekly Epub-Ahead-of-Print DOI Crossref status"
BODY = (
    "Hej biblioteket,\n\n"
    "Här kommer veckans DOI-statusrapport för Epub-Ahead-of-Print som CSV i bifogad fil.\n\n"
    "Vänliga hälsningar,\n"
    "Anders\n"
)


# ---- FUNCTIONS ----

def download_diva_csv():
    """Download fresh CSV from Diva and save as INPUT_CSV."""
    headers = {"User-Agent": USER_AGENT}
    r = requests.get(DIVA_URL, headers=headers, timeout=60)
    r.raise_for_status()
    with open(INPUT_CSV, "wb") as f:
        f.write(r.content)


def query_crossref(doi: str) -> dict:
    """Query a DOI in Crossref and return fields/flags."""
    url = CROSSREF_API_URL.format(doi)
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=20)
    except Exception as e:
        return {
            "status": "error",
            "http_status": None,
            "error": str(e),
            "volume": None,
            "issue": None,
            "article_number": None,
            "has_volume": False,
            "has_issue": False,
            "has_article_number": False,
        }

    if r.status_code != 200:
        return {
            "status": "http_error",
            "http_status": r.status_code,
            "error": None,
            "volume": None,
            "issue": None,
            "article_number": None,
            "has_volume": False,
            "has_issue": False,
            "has_article_number": False,
        }

    data = r.json().get("message", {})

    volume = data.get("volume")
    issue = data.get("issue")
    article_number = data.get("article-number") or data.get("article_number")

    return {
        "status": "ok",
        "http_status": r.status_code,
        "error": None,
        "volume": volume,
        "issue": issue,
        "article_number": article_number,
        "has_volume": bool(volume),
        "has_issue": bool(issue),
        "has_article_number": bool(article_number),
    }


def send_report(csv_path: str):
    """Send the OUTPUT_CSV as an email attachment via golonka.se SMTP."""
    msg = EmailMessage()
    msg["From"] = FROM_ADDR
    msg["To"] = ", ".join(TO_ADDRS)
    msg["Subject"] = SUBJECT
    msg["Reply-To"] = "aw@kth.se"
    msg.set_content(BODY)

    path = Path(csv_path)
    data = path.read_bytes()
    msg.add_attachment(
        data,
        maintype="text",
        subtype="csv",
        filename=path.name,
    )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
        server.login(SMTP_USER, SMTP_PASS)
        print("Logged in to SMTP, sending message...")
        server.send_message(msg)
        print("Message handed to SMTP server.")


def main():
    # 1) Hämta färsk CSV från Diva
    print("Downloading fresh DOI list from Diva...")
    download_diva_csv()

    # 2) Läs alla rader
    with open(INPUT_CSV, newline="", encoding="utf-8") as f_in:
        reader = csv.DictReader(f_in)
        rows = list(reader)

    # 3) Skriv utdata med progress bar
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f_out:
        # kombinera befintliga fält med våra extra
        base_fields = rows[0].keys() if rows else []
        extra_fields = [
            "status",
            "http_status",
            "error",
            "volume",
            "issue",
            "article_number",
            "has_volume",
            "has_issue",
            "has_article_number",
        ]
        fieldnames = list(dict.fromkeys(list(base_fields) + extra_fields))
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()

        for row in tqdm(rows, desc="Querying Crossref", unit="doi"):
            doi = row.get(DOI_FIELD, "").strip()
            if not doi:
                row.update({
                    "status": "no_doi",
                    "http_status": None,
                    "error": "missing DOI",
                    "volume": None,
                    "issue": None,
                    "article_number": None,
                    "has_volume": False,
                    "has_issue": False,
                    "has_article_number": False,
                })
                writer.writerow(row)
                continue

            info = query_crossref(doi)
            row.update(info)
            writer.writerow(row)

            time.sleep(SLEEP_SECONDS)

    # 4) Skicka rapporten via e‑post
    print(f"Sending report {OUTPUT_CSV} to {', '.join(TO_ADDRS)} via {SMTP_HOST}...")
    send_report(OUTPUT_CSV)
    print("Done.")


if __name__ == "__main__":
    main()
