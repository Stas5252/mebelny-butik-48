"""Migration and verification must preserve the existing product, including scripts."""
import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import json
import re

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('configure_search', ROOT/'tools/configure_search.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class SearchSetupTests(unittest.TestCase):
 def setUp(self):
  self.temp = tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
  for name in (*setup.PAGES,'robots.txt','sitemap.xml'):
   shutil.copy2(ROOT/name,self.root/name)
 def tearDown(self):self.temp.cleanup()

 def test_verification_preserves_body_and_is_idempotent(self):
  original={n:(self.root/n).read_text() for n in setup.PAGES}
  changes=setup.prepare(self.root,google='unit-test-google-token',yandex='0123456789abcdef')
  self.assertEqual(set(changes),set(setup.PAGES))
  for name,content in changes.items():
   self.assertEqual(content.split('</head>',1)[1],original[name].split('</head>',1)[1])
   self.assertEqual((self.root/name).read_text(),original[name])
   (self.root/name).write_text(content)
  self.assertEqual(setup.prepare(self.root,google='unit-test-google-token',yandex='0123456789abcdef'),{})

 def test_domain_migration_keeps_body_and_consistent_technical_urls(self):
  previous=re.search(r'<link rel="canonical" href="([^"]+)">',(self.root/'index.html').read_text()).group(1); destination='https://test.invalid/'
  changes=setup.prepare(self.root,base_url=destination)
  self.assertEqual(len(changes),len(setup.PAGES)+2)
  for name in setup.PAGES:
   old=(self.root/name).read_text();new=changes[name]
   self.assertEqual(new.split('</head>',1)[1],old.split('</head>',1)[1])
   self.assertNotIn(previous,new.split('</head>',1)[0])
   self.assertIn(destination,new.split('</head>',1)[0])
   for payload in re.findall(r'<script type="application/ld\+json">(.*?)</script>',new,re.S):json.loads(payload)
  self.assertIn(destination+'sitemap.xml',changes['robots.txt'])
  self.assertNotIn(previous,changes['sitemap.xml'])

 def test_domain_migration_updates_error_page_navigation_and_image_sitemap(self):
  changes=setup.prepare(self.root,base_url='https://test.invalid/')
  self.assertIn('404.html',list(changes))
  self.assertIn('<base href="https://test.invalid/">',changes['404.html'])
  self.assertIn('https://test.invalid/images/',changes['sitemap.xml'])

 def test_verification_update_preserves_existing_other_provider(self):
  first=setup.prepare(self.root,google='first-test-token')
  for name,content in first.items():(self.root/name).write_text(content)
  second=setup.prepare(self.root,yandex='0123456789abcdef')
  for content in second.values():
   self.assertIn('content="first-test-token"',content)
   self.assertIn('content="0123456789abcdef"',content)

 def test_missing_canonical_fails_before_any_write(self):
  path=self.root/'index.html';text=path.read_text();path.write_text(re.sub(r'<link rel="canonical"[^>]+>','',text))
  before=path.read_text()
  with self.assertRaises(ValueError):setup.prepare(self.root,google='unit-test-token')
  self.assertEqual(path.read_text(),before)

 def test_rejects_html_tokens_and_insecure_or_malformed_base(self):
  for value in ('<meta name="x">','placeholder token','https://example.com/?x=1'):
   with self.assertRaises(argparse.ArgumentTypeError):setup.valid_token(value)
  for value in ('http://example.com/','https://user:password@example.com/','https://example.com/?x=1','https://example.com/#x','https://example.com/"'):
   with self.assertRaises(argparse.ArgumentTypeError):setup.valid_base(value)
  self.assertEqual(setup.valid_base('https://example.com/site'),'https://example.com/site/')


if __name__=='__main__':unittest.main()
