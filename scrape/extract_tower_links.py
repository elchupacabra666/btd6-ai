# extract_tower_links.py
import re
from pathlib import Path
from bs4 import BeautifulSoup

SECTION_IDS = ["Primary_Monkeys", "Military_Monkeys", "Magic_Monkey", "Support_Monkeys"]


def extract_tower_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = {}

    for section_id in SECTION_IDS:
        span = soup.find("span", id=section_id)
        if span is None:
            print(f"WARNING: section {section_id} not found")
            continue
        heading = span.find_parent(["h2", "h3"])
        table = heading.find_next_sibling("table")
        if table is None:
            print(f"WARNING: no table after {section_id}")
            continue

        # Only td[rowspan="3"] cells hold a tower's own name+link — the
        # other two rows in each 3-row group don't repeat it, since the
        # cell spans across all three.
        for td in table.select('td[rowspan="3"]'):
            a = td.find("a", href=re.compile(r"^/wiki/"))
            if a is None:
                continue
            name = a.get_text(strip=True)
            href = a.get("href")
            if name and href:
                links[name] = "https://bloons.fandom.com" + href

    return links


if __name__ == "__main__":
    html_path = Path(__file__).parent / "html.txt"
    html = html_path.read_text(encoding="utf-8")
    links = extract_tower_links(html)

    print(f"Found {len(links)} tower links\n")
    output_path = Path(__file__).parent / "tower_links.txt"
    with open(output_path, "w") as f:
        for name, url in links.items():
            print(f"{name}: {url}")
            f.write(url + "\n")

    print(f"\nWrote {output_path} ({len(links)} URLs)")