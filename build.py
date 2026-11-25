#!/usr/bin/env python3
"""Builds index.html (embeds data/*.xlsx, site URL and favicon) plus robots.txt and sitemap.xml.
Usage:  python3 build.py [workbook.xlsx]      (SITE_URL=https://you.github.io/repo/ python3 build.py to change the address)"""
import base64, os, sys, pathlib, urllib.parse
root = pathlib.Path(__file__).parent
xl = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(root.glob('data/*.xlsx'))[0]
site = os.environ.get('SITE_URL', 'https://fiws.devs.surf/').rstrip('/') + '/'
fav = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="13" fill="#0B2239"/>'
       '<g transform="translate(10.5 12.8) scale(.8)"><rect width="36" height="8" fill="#00AEEF"/><rect x="42" width="12" height="8" fill="#00AEEF"/>'
       '<g fill="#fff"><rect y="16" width="12" height="32"/><rect x="12" y="16" width="22" height="12"/><rect x="42" y="16" width="12" height="32"/></g></g></svg>')
b = base64.b64encode(xl.read_bytes()).decode()
tpl = (root / 'src/index.template.html').read_text(encoding='utf-8')
out = tpl.replace('__B64__', b).replace('__SITE_URL__', site).replace('__FAVICON__', 'data:image/svg+xml,' + urllib.parse.quote(fav))
(root / 'index.html').write_text(out, encoding='utf-8')
(root / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {site}sitemap.xml\n', encoding='utf-8')
(root / 'sitemap.xml').write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{site}</loc></url></urlset>\n', encoding='utf-8')
print(f'Built index.html for {site} from {xl.name} ({len(out)//1024} KB)')