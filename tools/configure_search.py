#!/usr/bin/env python3
"""Install owner-supplied search verification and migrate technical URL metadata.

Only <head>, sitemap.xml and robots.txt may change. Body text, styles, images,
links and scripts stay byte-for-byte identical. Dry run unless --apply is set.
No analytics counter is installed and no external service is contacted.
"""
import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PAGES = ('index.html', 'configurator.html', 'privacy.html', 'consent.html', 'details.html')


def valid_token(value):
    if not re.fullmatch(r'[A-Za-z0-9_=-]{8,256}', value):
        raise argparse.ArgumentTypeError('Use the actual content value from the verification meta tag, without HTML.')
    return value


def valid_base(value):
    try:
        url = urlsplit(value)
        port = url.port
    except ValueError as error:
        raise argparse.ArgumentTypeError('Malformed HTTPS site URL.') from error
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or port or any(c.isspace() for c in value)
            or re.search(r'[<>"\'\\]', value)):
        raise argparse.ArgumentTypeError('Use a public HTTPS site URL without credentials, query, fragment or port.')
    return value.rstrip('/') + '/'


def prepare(root, base_url=None, google=None, yandex=None):
    originals = {name: (root / name).read_text() for name in PAGES}
    match = re.search(r'<link rel="canonical" href="([^"]+)">', originals['index.html'])
    if not match:
        raise ValueError('Missing home canonical; no files changed.')
    previous = match.group(1)
    if not previous.endswith('/'):
        raise ValueError('Home canonical must end in /; no files changed.')
    changes = {}
    for name, source in originals.items():
        head, separator, body = source.partition('</head>')
        if not separator:
            raise ValueError(f'Missing </head>: {name}; no files changed.')
        if base_url:
            head = head.replace(previous, base_url)
        for service, token in (('google-site-verification', google), ('yandex-verification', yandex)):
            if token is None:
                continue
            tag = f'<meta name="{service}" content="{html.escape(token, quote=True)}">'
            pattern = rf'<meta\b[^>]*\bname=["\']{service}["\'][^>]*>\s*'
            head = re.sub(pattern, '', head)
            head = head.rstrip() + '\n' + tag + '\n'
        updated = head + separator + body
        for payload in re.findall(r'<script type="application/ld\+json">(.*?)</script>', head, re.S):
            json.loads(payload)
        if updated != source:
            changes[name] = updated
    if base_url:
        for name in ('robots.txt', 'sitemap.xml'):
            source = (root / name).read_text()
            updated = source.replace(previous, base_url)
            if name == 'sitemap.xml':
                ET.fromstring(updated)
            if updated != source:
                changes[name] = updated
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', type=valid_base)
    parser.add_argument('--google-verification', type=valid_token)
    parser.add_argument('--yandex-verification', type=valid_token)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not any((args.base_url, args.google_verification, args.yandex_verification)):
        parser.error('Provide a new base URL or a real verification token.')
    changes = prepare(ROOT, args.base_url, args.google_verification, args.yandex_verification)
    if args.apply:
        for name, content in changes.items():
            (ROOT / name).write_text(content)
    print(json.dumps({'mode': 'applied' if args.apply else 'dry-run', 'changed_files': list(changes),
                      'body_preserved': True, 'analytics_installed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
