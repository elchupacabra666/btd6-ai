# scrape_costs.py
import re
import json
import time
from pathlib import Path

import cloudscraper
from bs4 import BeautifulSoup

DIFFICULTIES = ["Easy", "Medium", "Hard", "Impoppable"]
HEADERS = {"User-Agent": "Mozilla/5.0 (personal project cost scraper)"}


def to_int(s):
    return int(s.replace(",", "").replace("$", "").strip())


def tower_slug_from_title(soup):
    """'Dart Monkey (BTD6)' -> 'dart_monkey'"""
    title_tag = soup.find("title")
    title = title_tag.get_text() if title_tag else "unknown"
    name = title.split("(")[0].strip()
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def parse_base_cost(soup):
    """Reads the infobox 'Cost' row -> {difficulty: cost}."""
    cost_div = soup.select_one('div[data-source="cost"] .pi-data-value')
    if cost_div is None:
        return None
    text = cost_div.get_text(" ", strip=True)
    pairs = re.findall(r"\$([\d,]+)\s*\(\s*(\w+)", text)
    return {d: to_int(a) for a, d in pairs if d in DIFFICULTIES}


def parse_upgrade_paths(soup):
    """Returns {0: [tier1_costs, ...], 1: [...], 2: [...]}, each tier a
    {difficulty: cost} dict. Walks siblings after each 'Path N' heading
    until the next heading, collecting upgrade-box tables along the way."""
    paths = {0: [], 1: [], 2: []}
    path_headings = {"Path_1": 0, "Path_2": 1, "Path_3": 2}

    for heading_id, path_index in path_headings.items():
        span = soup.find("span", id=heading_id)
        if span is None:
            continue
        heading = span.find_parent(["h2", "h3", "h4"])
        if heading is None:
            continue

        tiers = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ("h2", "h3", "h4"):
                break
            if sibling.name != "table":
                continue
            title_cell = sibling.select_one(".bloons-upgradebox-title")
            if title_cell is None:
                continue
            tier_costs = {
                abbr.get("title"): to_int(abbr.get_text())
                for abbr in title_cell.select("abbr")
                if abbr.get("title") in DIFFICULTIES
            }
            if tier_costs:
                tiers.append(tier_costs)

        paths[path_index] = tiers

    return paths


def parse_tower_page(html):
    soup = BeautifulSoup(html, "html.parser")
    slug = tower_slug_from_title(soup)
    return slug, {"base_cost": parse_base_cost(soup), "upgrades": parse_upgrade_paths(soup)}

scraper = cloudscraper.create_scraper()  # replaces requests for this site

def fetch(url):
    resp = scraper.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def main(links_file="tower_links.txt", output_file="scraped_costs.json"):
    links = [
        line.strip()
        for line in Path(links_file).read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]

    all_data = {}
    for url in links:
        print(f"Fetching {url}")
        try:
            html = fetch(url)
            slug, data = parse_tower_page(html)
            all_data[slug] = data
            print(f"  -> {slug}: base={data['base_cost']}, "
                  f"path tiers={[len(t) for t in data['upgrades'].values()]}")
        except Exception as e:
            print(f"  FAILED: {e}")
        time.sleep(1)  # be polite to the wiki's servers

    Path(output_file).write_text(json.dumps(all_data, indent=2))
    print(f"\nDone. Wrote {len(all_data)} towers to {output_file}")


if __name__ == "__main__":
    main()