"""Collect chapter titles/links only; tutorial bodies are not mirrored."""
import json
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
AGENT = 'KnowledgeLibraryCatalog/1.0'
COURSES = {
    'Python': 'https://www.runoob.com/python3/python3-tutorial.html',
    'C++': 'https://www.runoob.com/cplusplus/cpp-tutorial.html',
    'Java': 'https://www.runoob.com/java/java-tutorial.html',
    'FastAPI': 'https://www.runoob.com/fastapi/fastapi-tutorial.html',
    'MySQL': 'https://www.runoob.com/mysql/mysql-tutorial.html',
    'Docker': 'https://www.runoob.com/docker/docker-tutorial.html',
}


class Links(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base = base; self.active = None; self.rows = {}

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.active = [dict(attrs).get('href', ''), []]

    def handle_data(self, text):
        if self.active is not None:
            self.active[1].append(text)

    def handle_endtag(self, tag):
        if tag != 'a' or self.active is None:
            return
        href, parts = self.active; self.active = None
        url = urlsplit(urljoin(self.base, href))
        prefix = urlsplit(self.base).path.rsplit('/', 1)[0] + '/'
        title = ' '.join(''.join(parts).split())
        if (url.hostname == 'www.runoob.com' and url.path.startswith(prefix)
                and url.path.endswith('.html') and title and len(title) < 150):
            link = urlunsplit(('https', url.netloc, url.path, '', ''))
            self.rows.setdefault(link, title)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    robots = RobotFileParser('https://www.runoob.com/robots.txt')
    with urlopen(Request(robots.url, headers={'User-Agent': AGENT}), timeout=25) as response:
        robots.parse(response.read().decode('utf-8').splitlines())
    target = ROOT / 'data' / 'runoob'; target.mkdir(parents=True, exist_ok=True)
    output = target / 'catalog.json'
    result = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'collected_at': datetime.now(timezone.utc).isoformat(), 'content_type': 'chapter_catalog_only', 'courses': []}
    for course, url in COURSES.items():
        if any(c['name'] == course for c in result['courses']):
            continue
        if not robots.can_fetch(AGENT, url):
            raise RuntimeError('Crawling disallowed: ' + url)
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=30) as response:
                    html = response.read().decode('utf-8')
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(2)
        parser = Links(url); parser.feed(html)
        if len(parser.rows) < 8:
            raise RuntimeError('Chapter list incomplete: ' + course)
        result['courses'].append({'name': course, 'url': url,
            'chapters': [{'url': link, 'title': title} for link, title in parser.rows.items()]})
        print(course, len(parser.rows), flush=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        time.sleep(1)
    (target / 'catalog.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Saved catalog:', target / 'catalog.json')


if __name__ == '__main__':
    main()
