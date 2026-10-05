import os
import unittest
from playwright.sync_api import sync_playwright

class AuditFixTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=sync_playwright().start()
  cls.browser=cls.p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop()
 def setUp(self):
  self.context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
  self.page=self.context.new_page();self.page.set_default_timeout(5000);self.page.goto('http://localhost:3000/',wait_until='domcontentloaded')
 def tearDown(self):self.context.close()
 def open_request_draft(self):
  self.page.evaluate('window.openContactDraft=(url)=>{window.auditDraft=url;};')
  self.page.locator('#mainForm [name="name"]').fill('Проверка заявки')
  self.page.locator('#mainForm [name="phone"]').fill('+7 (900) 000-00-00')
  self.page.locator('#mainForm [name="consent"]').check()
  self.page.locator('#mainForm button[type="submit"]').click()
  from urllib.parse import parse_qs,urlparse
  draft=urlparse(self.page.evaluate('window.auditDraft'))
  self.assertEqual(draft.path,'mebelbutik.48@yandex.ru')
  return parse_qs(draft.query)['body'][0]
 def test_map_load_requires_explicit_click(self):
  self.assertEqual(self.page.locator('#map iframe[src]').count(),0)
  self.page.locator('#loadMap').click()
  self.assertIn('oid=193848899924',self.page.locator('#map iframe').get_attribute('src'))
 def test_mobile_page_and_quiz_do_not_overflow(self):
  for width in (320,390,768,1440):
   self.page.set_viewport_size({'width':width,'height':844})
   self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width)
  self.page.set_viewport_size({'width':320,'height':844})
  for _ in range(3):self.page.locator('#kzNext').click()
  self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),320)
 def test_legal_documents_are_real_and_placeholder_identified(self):
  self.page.goto('http://localhost:3000/privacy.html')
  self.assertIn('Реквизиты уточняются',self.page.locator('#legalOperator').inner_text())
  self.assertEqual(self.page.locator('h1').count(),1)
  self.page.goto('http://localhost:3000/consent.html')
  self.assertIn('Согласие',self.page.locator('h1').inner_text())
 def test_contact_form_never_claims_unconfirmed_delivery(self):
  self.assertEqual(self.page.locator('#mainDone').count(),0)
  self.assertTrue(self.page.locator('#mainForm').is_visible())
  self.assertEqual(self.page.evaluate('window.contactSettings.email'),'mebelbutik.48@yandex.ru')
  self.assertEqual(self.page.locator('#contactEmailLink').get_attribute('href'),'mailto:mebelbutik.48@yandex.ru')
  self.page.locator('#mainForm [name="name"]').fill('Тест аудита')
  self.page.locator('#mainForm [name="phone"]').fill('+7 (900) 000-00-00')
  self.page.locator('#mainForm [name="comment"]').fill('Кухня & остров, 270 см')
  self.page.locator('#mainForm button[type="submit"]').click()
  self.assertIn('соглас',self.page.locator('#mainFormStatus').inner_text().lower())
  self.page.locator('#mainForm [name="consent"]').check()
  self.page.evaluate('window.openContactDraft=(url)=>{window.auditDraft=url;};')
  self.page.locator('#mainForm button[type="submit"]').click()
  draft=self.page.evaluate('window.auditDraft')
  self.assertTrue(draft.startswith('mailto:mebelbutik.48@yandex.ru?'))
  from urllib.parse import parse_qs,urlparse
  body=parse_qs(urlparse(draft).query)['body'][0]
  self.assertIn('Тест аудита',body);self.assertIn('+7 (900) 000-00-00',body);self.assertIn('Согласие',body)
  self.assertIn('Кухня & остров, 270 см',body)
  self.assertEqual(parse_qs(urlparse(draft).query)['subject'][0],'Заявка — Мебельный Бутик 48')
  with self.page.expect_download() as result:self.page.locator('#downloadContactDraft').click()
  from pathlib import Path
  saved=Path(result.value.path()).read_text()
  self.assertIn('Кому: mebelbutik.48@yandex.ru',saved)
  self.assertIn(body,saved)
  self.assertNotIn('Заявка отправлена',self.page.locator('#mainFormStatus').inner_text())
 def test_placeholder_email_prepares_local_draft_without_transmission(self):
  from pathlib import Path
  self.page.evaluate('window.contactSettings.email="orders@example.invalid";window.refreshContactMode();')
  self.assertTrue(self.page.locator('#mainForm').is_visible())
  self.assertIn('не настроен',self.page.locator('#contactEmailHelp').inner_text())
  self.page.evaluate('()=>{window.auditDraftCalls=0;window.openContactDraft=()=>{window.auditDraftCalls++;};}')
  self.page.locator('#mainForm [name="name"]').fill('Локальный черновик')
  self.page.locator('#mainForm [name="phone"]').fill('+7 (900) 000-00-00')
  self.page.locator('#mainForm [name="comment"]').fill('Шкаф под лестницей')
  self.page.locator('#mainForm [name="consent"]').check()
  self.page.locator('#mainForm button[type="submit"]').click()
  self.assertIn('не отправлена',self.page.locator('#mainFormStatus').inner_text())
  with self.page.expect_download() as result:self.page.locator('#downloadContactDraft').click()
  content=Path(result.value.path()).read_text()
  self.assertIn('Локальный черновик',content)
  self.assertIn('Шкаф под лестницей',content)
  self.assertIn('+7 (900) 000-00-00',content)
  self.assertEqual(self.page.evaluate('window.auditDraftCalls'),0)
  self.assertEqual(self.context.cookies(),[])
  self.assertEqual(self.page.evaluate('localStorage.length+sessionStorage.length'),0)

 def test_quiz_carries_selection_into_email_form(self):
  for _ in range(3):self.page.locator('#kzNext').click()
  self.page.locator('[data-msg="MAX"]').click()
  self.page.locator('#kzSubmit').click()
  comment=self.page.locator('#mainForm [name="comment"]').input_value()
  self.assertIn('Форма: Прямая',comment)
  self.assertIn('Способ связи: MAX',comment)
  self.assertEqual(self.page.locator('#kzPhone').count(),0)
  self.assertEqual(self.page.locator('#kzDone').count(),0)
  self.assertIn(comment,self.open_request_draft())
 def test_closed_mobile_menu_is_not_keyboard_focusable(self):
  self.assertTrue(self.page.locator('#mm').evaluate('e=>e.inert'))
  self.page.locator('#bg').click()
  self.assertFalse(self.page.locator('#mm').evaluate('e=>e.inert'))
  self.page.keyboard.press('Escape')
  self.assertTrue(self.page.locator('#mm').evaluate('e=>e.inert'))
  self.assertEqual(self.page.evaluate('document.activeElement.id'),'bg')

 def test_hero_defers_unused_slides_and_loads_selected_slide(self):
  self.assertEqual(self.page.locator('.hero__sl img[data-src]').count(),4)
  self.page.locator('.ix[data-i="3"]').click()
  self.page.wait_for_function('document.querySelector(".hero__sl.on img").naturalWidth>0')
  self.assertEqual(self.page.locator('.hero__sl img[data-src]').count(),3)
 def test_downloaded_description_matches_quiz_and_has_no_contact_data(self):
  for _ in range(3):self.page.locator('#kzNext').click()
  self.page.locator('#kzSubmit').click()
  with self.page.expect_download() as result:self.page.locator('#downloadProject').click()
  download=result.value
  self.assertTrue(download.suggested_filename.endswith('.txt'))
  from pathlib import Path
  content=Path(download.path()).read_text()
  self.assertIn('Подбор кухни:',content)
  self.assertNotIn('Телефон:',content)
 def test_configurator_stops_rendering_when_idle_and_updates_on_change(self):
  self.page.goto('http://localhost:3000/configurator.html',wait_until='networkidle')
  self.page.evaluate('()=>{window.auditRenderCount=0;const raf=window.requestAnimationFrame;window.requestAnimationFrame=function(callback){window.auditRenderCount++;return raf.call(window,callback);};}')
  self.page.wait_for_timeout(1500)
  self.page.evaluate('window.auditRenderCount=0')
  self.page.wait_for_timeout(600)
  self.assertEqual(self.page.evaluate('window.auditRenderCount'),0,'Idle scene keeps consuming GPU/CPU')
  self.page.locator('#frameSwatches [data-v="champagne"]').click()
  self.page.wait_for_function('window.auditRenderCount>0')
  self.assertGreater(self.page.locator('#viewport canvas').count(),0)

 def test_configurator_passes_accurate_cost_and_russian_labels(self):
  self.page.goto('http://localhost:3000/configurator.html')
  self.page.locator('#frameSwatches [data-v="champagne"]').click()
  price=self.page.locator('#costPrice').inner_text()
  self.page.locator('#costOrder').click()
  self.page.wait_for_url('**/index.html#cta')
  text=self.page.locator('#projectText').input_value()
  self.assertIn('Шампань браш',text)
  import re
  self.assertEqual(re.findall(r'\d+',price),re.findall(r'\d+',text.split('Предварительный расчёт:')[1]))
  self.assertIn(text,self.open_request_draft())

if __name__=='__main__':unittest.main(verbosity=2)
