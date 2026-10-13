"""Static crawl checks for the existing public pages; no external requests."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://stas5252.github.io/mebelny-butik-48/'
PAGES = ('index.html', 'configurator.html', 'privacy.html', 'consent.html', 'details.html')

class Page(HTMLParser):
 def __init__(self, path):
  super().__init__(); self.tags=[]; self.ids=set(); self.headings=[]; self.title=[]; self.schemas=[]; self.active=None; self.buffer=''
  self.feed(path.read_text())
 def handle_starttag(self, tag, attrs):
  attrs=dict(attrs); self.tags.append((tag,attrs))
  if 'id' in attrs:self.ids.add(attrs['id'])
  if tag in ('h1','h2','h3','title') or (tag=='script' and attrs.get('type')=='application/ld+json'):
   self.active=tag;self.buffer=''
 def handle_data(self, data):
  if self.active:self.buffer+=data
 def handle_endtag(self, tag):
  if tag==self.active:
   text=' '.join(self.buffer.split())
   if tag=='title':self.title.append(text)
   elif tag=='script':self.schemas.append(json.loads(self.buffer))
   else:self.headings.append((int(tag[1]),text))
   self.active=None
 def values(self, tag, match, attr):
  return [a.get(attr,'') for t,a in self.tags if t==tag and all(a.get(k)==v for k,v in match.items())]

class SEOTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.pages={name:Page(ROOT/name) for name in PAGES}
 def test_unique_page_metadata_and_one_main_heading(self):
  titles=[];descriptions=[]
  for name,p in self.pages.items():
   with self.subTest(page=name):
    self.assertEqual(len(p.title),1);self.assertTrue(p.title[0]);titles.extend(p.title)
    desc=p.values('meta',{'name':'description'},'content');self.assertEqual(len(desc),1);self.assertTrue(desc[0]);descriptions.extend(desc)
    self.assertEqual(sum(level==1 for level,_ in p.headings),1)
    levels=[level for level,_ in p.headings]
    for previous,next_level in zip(levels,levels[1:]):self.assertLessEqual(next_level,previous+1)
    self.assertEqual(p.values('html',{},'lang'),['ru'])
    canonical=p.values('link',{'rel':'canonical'},'href');self.assertEqual(canonical,[BASE+('' if name=='index.html' else name)])
  self.assertEqual(len(set(titles)),len(titles));self.assertEqual(len(set(descriptions)),len(descriptions))
 def test_sitemap_contains_only_indexable_canonical_pages(self):
  expected=set()
  for name,p in self.pages.items():
   robots=p.values('meta',{'name':'robots'},'content')
   self.assertEqual(len(robots),1)
   if 'noindex' not in robots[0]:expected.update(p.values('link',{'rel':'canonical'},'href'))
  ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
  tree=ET.parse(ROOT/'sitemap.xml');locations=[node.text for node in tree.findall('s:url/s:loc',ns)]
  self.assertEqual(set(locations),expected);self.assertEqual(len(locations),len(expected))
 def test_internal_links_assets_and_fragments_resolve(self):
  for name,p in self.pages.items():
   for tag,attrs in p.tags:
    value=attrs.get('src') if tag in ('script','img') else attrs.get('href') if tag in ('a','link') else None
    if not value:continue
    url=urlsplit(value)
    if url.scheme and not value.startswith(BASE):continue
    relative=value[len(BASE):] if value.startswith(BASE) else value
    u=urlsplit(relative);path=unquote(u.path) or name
    target=ROOT/path
    with self.subTest(page=name,url=value):
     self.assertTrue(target.is_file(),f'Missing internal target: {target}')
     if u.fragment and path.endswith('.html'):
      document=self.pages.get(path) or Page(target)
      self.assertIn(unquote(u.fragment),document.ids)
 def test_structured_data_matches_contacts_without_invented_ratings(self):
  home=self.pages['index.html'].schemas;self.assertEqual(len(home),1)
  graph=home[0]['@graph'];business=next(x for x in graph if x.get('@id')==BASE+'#business')
  self.assertEqual(business['@type'],'FurnitureStore')
  self.assertEqual(business['telephone'],'+79042822376');self.assertEqual(business['email'],'mebelbutik.48@yandex.ru')
  self.assertEqual(business['openingHoursSpecification'][0]['closes'],'19:00')
  self.assertNotIn('geo',business);self.assertNotIn('postalCode',business['address'])
  self.assertTrue(any('max.ru/' in x for x in business['sameAs']))
  for p in self.pages.values():
   for schema in p.schemas:
    text=json.dumps(schema)
    self.assertNotIn('aggregateRating',text);self.assertNotIn('FAQPage',text)
  app=self.pages['configurator.html'].schemas[0]['@graph']
  self.assertIn('WebApplication',[x['@type'] for x in app]);self.assertIn('BreadcrumbList',[x['@type'] for x in app])
 def test_social_preview_matches_canonical_and_page_summary(self):
  for name in ('index.html','configurator.html'):
   p=self.pages[name]
   self.assertEqual(p.values('meta',{'property':'og:title'},'content'),p.title)
   self.assertEqual(p.values('meta',{'property':'og:description'},'content'),p.values('meta',{'name':'description'},'content'))
   self.assertEqual(p.values('meta',{'property':'og:url'},'content'),p.values('link',{'rel':'canonical'},'href'))
   images=p.values('meta',{'property':'og:image'},'content');self.assertEqual(len(images),1)
   self.assertTrue((ROOT/images[0].removeprefix(BASE)).is_file())

if __name__=='__main__':unittest.main()
