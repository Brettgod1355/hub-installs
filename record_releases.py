"""Record each new version of a watched plugin in data/releases.csv, for the chart's release markers.

Run: python record_releases.py   (after check_health.py, which writes data/health.json)

data/health.json carries the version the Plugin Hub serves for every watched plugin. A plugin whose
status is ok and whose version differs from the last row recorded for it gets a row dated today (UTC).
A plugin seen for the first time gets one too: that is its release on the Hub. The rows before
2026-11-01 were filled in by hand from the merged runelite/plugin-hub pull requests.
"""
import csv
import datetime
import json
import os
import sys

from fetch_installs import csv_text, write_text

ROOT = os.path.dirname(os.path.abspath(__file__))
HEADER = ["date", "plugin", "version"]


class ReleaseError(Exception):
    pass


def read_releases(path):
    """The rows of releases.csv, oldest first; none when the file is not there yet."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != HEADER:
            raise ReleaseError("%s has an unexpected header %r" % (path, header))
        return [row for row in reader if len(row) == 3]


def served_versions(health):
    """{slug: version} for the watched plugins players can install now."""
    plugins = health.get("plugins") if isinstance(health, dict) else None
    versions = {}
    for p in plugins if isinstance(plugins, list) else []:
        if not isinstance(p, dict) or p.get("status") != "ok":
            continue
        slug, version = p.get("slug"), p.get("version")
        if isinstance(slug, str) and slug and isinstance(version, str) and version:
            versions[slug] = version
    return versions


def new_rows(rows, versions, date):
    last = {}
    for _, slug, version in rows:
        last[slug] = version
    return [[date, slug, v] for slug, v in sorted(versions.items()) if last.get(slug) != v]


def run(root=ROOT, today=None):
    date = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    data_dir = os.path.join(root, "data")
    health_path = os.path.join(data_dir, "health.json")
    if not os.path.exists(health_path):
        print("No data/health.json yet; nothing to record.")
        return []
    with open(health_path, encoding="utf-8") as f:
        try:
            health = json.load(f)
        except ValueError as e:
            raise ReleaseError("data/health.json is not JSON: %s" % e)
    path = os.path.join(data_dir, "releases.csv")
    rows = read_releases(path)
    added = new_rows(rows, served_versions(health), date)
    if added:
        rows = sorted(rows + added, key=lambda row: (row[0], row[1]))
        write_text(path, csv_text(HEADER, rows))
    for _, slug, version in added:
        print("released: %s %s" % (slug, version))
    return added


def main(root=ROOT):
    try:
        run(root)
    except (ReleaseError, OSError, csv.Error) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
