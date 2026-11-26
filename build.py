#!/usr/bin/env python3
"""Zero Track Blog static build: posts-md/*.md -> posts/<slug>.html + index.html + feed.xml + sitemap.xml.
Standalone site, zero external requests (self-hosted fonts, no JS data dependency)."""
import json, os, re, subprocess, html as htmlmod
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'posts-md')
OUT = os.path.join(ROOT, 'posts')
BASE = 'https://tawffik.github.io/blog'
SITE = 'Zero Track Blog'

def md2html(text):
    return subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html5', '--wrap=none'],
                          input=text, capture_output=True, text=True, check=True).stdout.strip()

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%230c0e11'/%3E"
           "%3Ctext x='6' y='22' font-family='monospace' font-size='14' font-weight='bold' fill='%23a3d426'%3EZT%3C/text%3E"
           "%3Crect x='21' y='18' width='6' height='3' fill='%23a3d426'/%3E%3C/svg%3E")

def head(title, desc, base):
    return f'''<!DOCTYPE html>
<html lang="en" dir="ltr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<title>{title}</title>
<link rel="icon" href="{FAVICON}">
<link rel="stylesheet" href="{base}static/fonts.css?v=1">
<link rel="stylesheet" href="{base}static/style.css?v=1">
<link rel="alternate" type="application/rss+xml" title="{SITE}" href="{BASE}/feed.xml">
</head>
<body>
<header><nav class="nav" id="nav" data-base="{base}"></nav></header>'''

def foot(base):
    return '''<footer><div class="in">Zero Track Sec · understand before you break · Every claim ties to a checkable record. ·
<a href="https://github.com/Tawffik" target="_blank" rel="noopener">GitHub: Tawffik ↗</a></div></footer>
<script src="''' + base + '''static/nav.js?v=1"></script>
</body>
</html>
'''

POST_TMPL = head('{title} — ' + SITE, '{desc}', '../') + '''
<main class="post-page">
  <p style="margin-bottom:18px"><a href="../index.html">&larr; All posts</a></p>
  <div class="hero">
  <p class="eyebrow">{eyebrow}</p>
  <h1>{title}</h1>
  <p class="sub">{meta}</p>
  </div>
  <article class="post">
{body}
  </article>
  <div class="post-source">Source markdown: <a href="{source_url}" target="_blank" rel="noopener">posts-md/{filename} ↗</a></div>
</main>
''' + foot('../')

INDEX_TMPL = head(SITE + ' — security research, verified work only',
                  'Original security research, writeups and engineering notes from Zero Track Lab. Verified work only.', '') + '''
<main>
  <div class="hero">
  <p class="eyebrow">Zero Track Lab</p>
  <h1>Research &amp; Writeups</h1>
  <p class="sub">Original security research and engineering notes. Every claim is tied to a
  checkable record — the markdown source of each post is linked at its end.</p>
  </div>
  <div class="post-list">
{cards}
  </div>
</main>
''' + foot('')

CARD = '''    <a class="post-card" href="posts/{slug}.html">
      <span class="post-date">{date}</span>
      <span class="post-title">{title}</span>
      <span class="post-excerpt">{excerpt}&hellip;</span>
      <span class="post-read">Read post &rarr;</span>
    </a>'''

posts = []
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith('.md'): continue
    raw = open(os.path.join(SRC, fn)).read()
    title = raw.split('\n')[0].lstrip('# ').strip()
    m = re.search(r'^##\s+ملخص عربي\s*$', raw, re.M)
    en_raw, ar_html = raw, ''
    if m:
        en_raw = raw[:m.start()]
        ar_html = '<div class="post-ar" dir="rtl" lang="ar">' + md2html(raw[m.start():]) + '</div>'
    body_md = '\n'.join(en_raw.split('\n')[2:])
    meta = ''
    bm = re.match(r'^\*([^*]+)\*\s*$', body_md.strip().split('\n')[0])
    if bm:
        meta = bm.group(1).strip().replace('`', '')
        body_md = body_md.strip().split('\n', 1)[1]
    body = md2html(body_md) + '\n' + ar_html
    slug = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', fn[:-3])
    date = fn[:10]
    raw_ex = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body)).strip()
    cut = raw_ex[:240]
    dot = cut.rfind('. ')
    excerpt = (cut[:dot+1] if dot > 120 else cut[:cut.rfind(' ')])
    desc = excerpt[:155]
    source_url = f'https://github.com/Tawffik/blog/blob/main/posts-md/{fn}'
    page = POST_TMPL.format(title=htmlmod.escape(title, quote=True),
                            desc=htmlmod.escape(desc, quote=True),
                            eyebrow='Research · ' + date,
                            meta=htmlmod.escape(meta), body=body,
                            source_url=source_url, filename=fn)
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, slug + '.html'), 'w').write(page)
    posts.append(dict(slug=slug, title=title, date=date, excerpt=excerpt))
    print('built', slug)

cards = '\n'.join(CARD.format(slug=p['slug'], date=p['date'],
                              title=htmlmod.escape(p['title']),
                              excerpt=htmlmod.escape(p['excerpt'])) for p in reversed(posts))
open(os.path.join(ROOT, 'index.html'), 'w').write(INDEX_TMPL.format(cards=cards))

# RSS
items = []
for p in reversed(posts):
    d = datetime.strptime(p['date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
    items.append(f'''    <item>
      <title>{htmlmod.escape(p["title"])}</title>
      <link>{BASE}/posts/{p["slug"]}.html</link>
      <guid>{BASE}/posts/{p["slug"]}.html</guid>
      <pubDate>{d.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
      <description>{htmlmod.escape(p["excerpt"])}</description>
    </item>''')
open(os.path.join(ROOT, 'feed.xml'), 'w').write(f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{SITE}</title>
    <link>{BASE}/</link>
    <description>Original security research and engineering notes from Zero Track Lab. Verified work only.</description>
{chr(10).join(items)}
  </channel>
</rss>
''')

# Sitemap
urls = [f'  <url><loc>{BASE}/</loc></url>'] + [
    f'  <url><loc>{BASE}/posts/{p["slug"]}.html</loc><lastmod>{p["date"]}</lastmod></url>' for p in posts]
open(os.path.join(ROOT, 'sitemap.xml'), 'w').write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + '\n'.join(urls) + '\n</urlset>\n')
print('built index.html, feed.xml, sitemap.xml with', len(posts), 'post(s)')
