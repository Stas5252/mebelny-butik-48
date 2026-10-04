import os
import unittest
from playwright.sync_api import sync_playwright

class GalleryTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.playwright=sync_playwright().start()
  cls.browser=cls.playwright.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 @classmethod
 def tearDownClass(cls):
  cls.browser.close();cls.playwright.stop()
 def setUp(self):
  self.page=self.browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
  self.page.goto('http://localhost:3000/',wait_until='domcontentloaded')
 def tearDown(self):self.page.close()
 def visible_count(self):return self.page.locator('#gw .wk:not(.hide)').count()
 def test_initial_batch_and_load_more(self):
  self.assertEqual(self.visible_count(),9)
  more=self.page.locator('#worksMore')
  self.assertTrue(more.is_visible())
  more.click()
  self.assertEqual(self.visible_count(),18)
  total=self.page.locator('#gw .wk').count()
  while more.is_visible():more.click()
  self.assertEqual(self.visible_count(),total)
  self.assertFalse(more.is_visible())
 def test_filter_resets_batch_and_does_not_leak_categories(self):
  self.page.locator('#flt [data-f="wardrobe"]').click()
  count=self.page.locator('#gw .wk[data-cat="wardrobe"]').count()
  self.assertEqual(self.visible_count(),min(9,count))
  self.assertEqual(self.page.locator('#gw .wk:not(.hide):not([data-cat="wardrobe"])').count(),0)
  while self.page.locator('#worksMore').is_visible():self.page.locator('#worksMore').click()
  self.assertEqual(self.visible_count(),count)
  self.page.locator('#flt [data-f="bathroom"]').click()
  baths=self.page.locator('#gw .wk[data-cat="bathroom"]').count()
  self.assertEqual(self.visible_count(),min(9,baths))
  self.assertEqual(self.page.locator('#gw .wk:not(.hide):not([data-cat="bathroom"])').count(),0)
  self.page.locator('#flt [data-f="all"]').click()
  self.assertEqual(self.visible_count(),9)
 def test_project_angles_and_keyboard_navigation(self):
  self.page.locator('#flt [data-f="wardrobe"]').click()
  card=self.page.locator('#gw .wk[data-photos]').filter(has=self.page.locator('img[src$="client_work_01.jpg"]')).first
  self.assertEqual(card.count(),1,'Actual wardrobe photos are missing')
  card.click()
  self.assertTrue(self.page.locator('#lb').is_visible())
  self.assertEqual(self.page.locator('#lbImg').get_attribute('src'),'images/client_work_01.jpg')
  self.page.locator('#lbNext').click()
  self.assertEqual(self.page.locator('#lbImg').get_attribute('src'),'images/client_work_02.jpg')
  self.page.keyboard.press('ArrowLeft')
  self.assertEqual(self.page.locator('#lbImg').get_attribute('src'),'images/client_work_01.jpg')
  self.page.keyboard.press('Escape')
  self.assertFalse(self.page.locator('#lb').is_visible())
  self.assertTrue(card.evaluate('(el)=>el===document.activeElement'))
 def test_price_preview_does_not_keep_project_navigation(self):
  self.page.locator('#flt [data-f="wardrobe"]').click()
  card=self.page.locator('#gw .wk[data-photos]:not(.hide)').first
  self.assertGreater(card.count(),0)
  card.click();self.page.keyboard.press('Escape')
  image=self.page.locator('#kpCard1 .kp-slide.active img, #kpCard1 .kp-slide.on img').first
  if image.count()==0:image=self.page.locator('#kpCard1 .kp-slide img').first
  image.click(force=True)
  self.assertTrue(self.page.locator('#lb').is_visible())
  self.assertFalse(self.page.locator('#lbNext').is_visible())
  self.assertFalse(self.page.locator('#lbPrev').is_visible())

if __name__=='__main__':unittest.main(verbosity=2)
