"""Download factor returns from the Kenneth R. French Data Library into ``data/``.

The files are free and need no key. They are not committed: the library's page
carries a copyright notice and no licence. A manifest records the download
time, the URL, a checksum and the last month in each file.

Usage:
    uv run python scripts/fetch_data.py [--data-dir data] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from ballast.data import FILES, MANIFEST_NAME
from ballast.french import parse_french_csv

BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
USER_AGENT = "ballast-fetch/0.1 (research replication script)"


def download(url: str) -> bytes:
    """Fetch ``url`` and return the body."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        body: bytes = response.read()
    return body


def extract_single_csv(archive: bytes) -> str:
    """Return the text of the one CSV inside a French zip archive."""
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if len(names) != 1:
            raise ValueError(f"expected one CSV in archive, found {names}")
        return zf.read(names[0]).decode("latin-1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--force", action="store_true", help="download even if files exist")
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = data_dir / MANIFEST_NAME
    if manifest_path.exists() and not args.force:
        print(f"{manifest_path} exists; use --force to download again")
        return 0

    entries = {}
    for spec in FILES:
        url = BASE_URL + spec.archive
        print(f"fetching {url}")
        archive = download(url)
        text = extract_single_csv(archive)
        (data_dir / spec.csv_name).write_text(text, encoding="utf-8", newline="\n")
        table = parse_french_csv(text, spec.frequency)
        entries[spec.csv_name] = {
            "url": url,
            "sha256_zip": hashlib.sha256(archive).hexdigest(),
            "frequency": spec.frequency,
            "columns": list(table.columns),
            "first_period": str(table.index[0]),
            "last_period": str(table.index[-1]),
            "rows": len(table),
        }
    manifest = {
        "source": "Kenneth R. French Data Library",
        "source_page": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "downloaded_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
