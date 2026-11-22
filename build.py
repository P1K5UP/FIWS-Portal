#!/usr/bin/env python3
"""Builds index.html by embedding data/*.xlsx into src/index.template.html.
Usage: python3 build.py [path/to/workbook.xlsx]"""
import base64, glob, sys, pathlib
root = pathlib.Path(__file__).parent
xl = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(root.glob('data/*.xlsx'))[0]
b = base64.b64encode(xl.read_bytes()).decode()
out = (root / 'src/index.template.html').read_text().replace('__B64__', b)
(root / 'index.html').write_text(out)
print(f'Built index.html from {xl.name} ({len(out)//1024} KB)')
