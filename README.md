## DiVA Epub Ahead‑of‑Print → Crossref Checker

This script automates checking whether “Epub Ahead of Print” publications in DiVA have received final bibliographic details in Crossref.

It:

- Downloads a CSV (`dois_input.csv`) containing all DOIs for publications with the status **“Epub Ahead of Print”** for a specific institution in DiVA.
- Queries the Crossref API for each DOI and checks whether fields such as **volume**, **issue**, and **article number** are now available.
- Writes the results to `dois_with_status.csv`, where you can see, for each DOI, whether these fields are present and the values that Crossref currently holds. This makes it easy to identify which records in your local system can be updated.
- Sends `dois_with_status.csv` as an email attachment via a configurable SMTP server (in this case the `anders@golonka.se` account) to one or more recipients, so the weekly status report lands automatically in their inboxes.

To adapt the script for another institution:

- Update the **DiVA export URL** (institution‑specific parameters) near the top of the file.
- Adjust the **input/output filenames** if needed.
- Configure the **SMTP settings** (server, port, username, password, From, recipient list) to match your local mail environment.


## Example cron configuration

To run the script every **Friday at 08:00** and log its output:

```cron
0 8 * * 5 cd /home/aw/epub_ahead && /home/aw/venv/bin/python check_crossref_epub.py >> /home/aw/epub_ahead/epub_check.log 2>&1
```

- `0 8 * * 5` – run at 08:00 every Friday.
- `cd /home/aw/epub_ahead` – ensures the script runs in the project directory (so relative paths like `dois_input.csv` work).
- `/home/aw/venv/bin/python check_crossref_epub.py` – uses your virtual environment’s Python to run the script.
- `>> ...epub_check.log 2>&1` – appends both stdout and stderr to `epub_check.log` so you can review what happened during each run.

