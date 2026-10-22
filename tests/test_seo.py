"""Static crawl checks for the existing public pages; no external requests."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = re.search(r'<link rel="canonical" href="([^"]+)">',(ROOT/'index.html').read_text()).group(1)
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

 def test_sitemap_exposes_original_gallery_images_and_service_photos(self):
  home=self.pages['index.html'];expected=set()
  for tag,attrs in home.tags:
   if attrs.get('data-photos'):
    expected.update(BASE+photo['src'] for photo in json.loads(attrs['data-photos']))
  ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','i':'http://www.google.com/schemas/sitemap-image/1.1'}
  tree=ET.parse(ROOT/'sitemap.xml')
  entry=next(node for node in tree.findall('s:url',ns) if node.findtext('s:loc',namespaces=ns)==BASE)
  images=[node.text for node in entry.findall('i:image/i:loc',ns)]
  self.assertTrue(expected)
  self.assertTrue(expected.issubset(set(images)),f'{len(expected-set(images))} original gallery images are missing')
  self.assertEqual(len(images),len(set(images)));self.assertLessEqual(len(images),1000)
  for value in images:
   self.assertTrue(value.startswith(BASE+'images/'))
   self.assertTrue((ROOT/value.removeprefix(BASE)).is_file(),value)

 def test_primary_image_metadata_matches_the_shared_preview(self):
  for name in ('index.html','configurator.html'):
   page=self.pages[name];url=page.values('meta',{'property':'og:image'},'content')[0]
   labels=page.values('meta',{'name':'twitter:image:alt'},'content')
   self.assertEqual(len(labels),1);self.assertTrue(labels[0])
   self.assertEqual(page.values('meta',{'property':'og:image:type'},'content'),['image/jpeg'])
   graph=page.schemas[0]['@graph'];webpage=next(n for n in graph if n['@type']=='WebPage')
   photo=next(n for n in graph if n.get('@id')==webpage['primaryImageOfPage']['@id'])
   self.assertEqual(photo['@type'],'ImageObject');self.assertEqual(photo['contentUrl'],url)
   self.assertEqual(photo['width'],int(page.values('meta',{'property':'og:image:width'},'content')[0]))
   self.assertEqual(photo['height'],int(page.values('meta',{'property':'og:image:height'},'content')[0]))

 def test_hero_preload_selects_the_same_responsive_file_as_the_image(self):
  home=self.pages['index.html'];hero=next(a for t,a in home.tags if t=='img' and a.get('fetchpriority')=='high')
  preload=[a for t,a in home.tags if t=='link' and a.get('rel')=='preload' and a.get('as')=='image']
  self.assertEqual(len(preload),1)
  self.assertEqual(preload[0]['href'],hero['src'])
  self.assertEqual(preload[0]['imagesrcset'],hero['srcset'])
  self.assertEqual(preload[0]['imagesizes'],hero['sizes'])

 def test_custom_error_page_is_not_indexed_and_navigation_survives_nested_urls(self):
  from urllib.parse import urljoin
  self.assertTrue((ROOT/'404.html').is_file(),'Missing custom error page')
  page=Page(ROOT/'404.html')
  self.assertEqual(page.values('meta',{'name':'robots'},'content'),['noindex,follow'])
  self.assertEqual(page.values('base',{},'href'),[BASE])
  self.assertEqual(page.values('link',{'rel':'canonical'},'href'),[])
  links=page.values('a',{},'href')
  self.assertEqual(urljoin(BASE,next(href for href in links if href=='./')),BASE)
  self.assertTrue(any(urljoin(BASE,href)==BASE+'#contacts' for href in links))
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

 def test_service_entities_match_visible_directions_and_real_anchors(self):
  home=self.pages['index.html'];graph=home.schemas[0]['@graph']
  services=[node for node in graph if node['@type']=='Service']
  names=[text for _,text in home.headings if text in [s['name'] for s in services]]
  self.assertEqual([s['name'] for s in services],names)
  self.assertEqual(len(services),7)
  for service in services:
   self.assertIn(urlsplit(service['url']).fragment,home.ids)
   self.assertEqual(service['provider'],{'@id':BASE+'#business'})
   self.assertEqual(service['areaServed']['name'],'Липецк')
   self.assertNotIn('offers',service)
  catalog=next(node for node in graph if node['@id']==BASE+'#services')
  self.assertEqual(catalog['numberOfItems'],len(services))
  self.assertEqual([x['item']['@id'] for x in catalog['itemListElement']],[s['@id'] for s in services])

 def test_optional_verification_has_no_placeholders_or_unrequested_analytics(self):
  for name,page in self.pages.items():
   for service in ('google-site-verification','yandex-verification'):
    values=page.values('meta',{'name':service},'content')
    self.assertLessEqual(len(values),1,name)
    for value in values:
     self.assertRegex(value,r'^[A-Za-z0-9_=-]{8,256}$')
     self.assertFalse(any(marker in value.lower() for marker in ('placeholder','unit-test','replace-me','your-token')),name)
   scripts=page.values('script',{},'src')
   self.assertFalse(any('mc.yandex.ru' in url or 'googletagmanager.com' in url for url in scripts),name)

if __name__=='__main__':unittest.main()
