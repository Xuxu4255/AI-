"""Validate lesson links and prepare the original study-note import manifest."""
import json
import sys
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from runoob_learning_notes import NOTES

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'runoob'
AGENT = 'KnowledgeLibraryCatalog/1.0'


class Title(HTMLParser):
    def __init__(self):
        super().__init__(); self.inside = False; self.value = ''
    def handle_starttag(self, tag, attrs):
        if tag == 'title': self.inside = True
    def handle_endtag(self, tag):
        if tag == 'title': self.inside = False
    def handle_data(self, text):
        if self.inside: self.value += text


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    catalog = json.loads((DATA / 'catalog.json').read_text(encoding='utf-8'))
    courses = {c['name']: c for c in catalog['courses']}
    cache_path = DATA / 'verified_links.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    robots = RobotFileParser('https://www.runoob.com/robots.txt'); robots.read()
    rows = []
    for course, notes in NOTES.items():
        chapters = {c['url'].rsplit('/', 1)[1].removesuffix('.html') if sys.version_info >= (3,9) else c['url'].rsplit('/', 1)[1][:-5]: c for c in courses[course]['chapters']}
        for slug, title, keywords, body, code in notes:
            if slug not in chapters:
                raise ValueError('Lesson not found in collected catalog: ' + slug)
            source = chapters[slug]; url = source['url']
            if not robots.can_fetch(AGENT, url): raise RuntimeError('Crawling disallowed: ' + url)
            if url not in cache:
                for attempt in range(3):
                    try:
                        with urlopen(Request(url, headers={'User-Agent': AGENT}), timeout=20) as response:
                            page = response.read().decode('utf-8')
                            if response.status != 200: raise ValueError('Unexpected response')
                        parser = Title(); parser.feed(page)
                        if '菜鸟' not in parser.value: raise ValueError('Unexpected page title: ' + url)
                        cache[url] = {'title': parser.value.strip(), 'checked_at': datetime.now(timezone.utc).isoformat(), 'http_status': 200}
                        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
                        break
                    except OSError:
                        if attempt == 2: raise
                        time.sleep(2)
                time.sleep(.6)
            content = body + '\n\n示例（自主编写，部分片段需放入完整程序上下文）：\n' + code
            content += '\n\n资料性质：自主整理的简短学习笔记，不是菜鸟教程原文。完整教程请通过来源链接阅读。'
            rows.append({'key': course + ':' + slug, 'category': course, 'title': course + '｜' + title,
                'summary': body, 'keyword': course + ' ' + keywords, 'content': content,
                'source_name': '菜鸟教程｜' + source['title'], 'source_url': url})
        print('Prepared', course, len(notes), flush=True)
    assert len(rows) == 96 and len({row['key'] for row in rows}) == len(rows)
    (DATA / 'notes.json').write_text(json.dumps({'generated_at': datetime.now(timezone.utc).isoformat(),
        'kind': 'original_study_notes_with_runoob_references', 'items': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Ready:', len(rows), 'notes, every source link checked')


if __name__ == '__main__': main()
