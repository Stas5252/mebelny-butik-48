import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

class RequestFormTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.p=sync_playwright().start();cls.browser=cls.p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 @classmethod
 def tearDownClass(cls):cls.browser.close();cls.p.stop()
 def setUp(self):
  self.context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
  self.page=self.context.new_page()
  self.page.goto('http://localhost:3000/',wait_until='domcontentloaded')
  self.page.evaluate('window.contactSettings.requestsEnabled=true;window.refreshContactMode();')
  self.page.evaluate('()=>{window.openContactDraft=()=>{throw new Error("Automatic mode opened mailto");};}')
 def tearDown(self):self.context.close()
 def fill(self):
  self.page.locator('#mainForm [name=name]').fill('Татьяна')
  self.page.locator('#mainForm [name=phone]').fill('+7 (900) 123-45-67')
  self.page.locator('#mainForm [name=comment]').fill('Кухня & остров, 270 см')
  self.page.locator('#mainForm [name=consent]').check()
 def test_success_sends_all_fields_to_backend_and_prevents_double_submit(self):
  sent=[]
  def respond(route):
   p=route.request.post_data_json;sent.append(p)
   route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'requestId':p['requestId']}))
  self.page.route('**/api/request.php',respond)
  self.assertEqual(self.page.locator('#mainForm button[type=submit]').inner_text(),'Отправить заявку')
  self.fill()
  self.page.evaluate('()=>{const f=document.getElementById("mainForm");f.requestSubmit();f.requestSubmit();}')
  self.page.wait_for_function('document.getElementById("mainFormStatus").textContent.includes("Заявка отправлена")')
  self.assertEqual(len(sent),1);self.assertEqual(sent[0]['name'],'Татьяна')
  self.assertEqual(sent[0]['comment'],'Кухня & остров, 270 см')
  self.assertTrue(sent[0]['consent']);self.assertEqual(sent[0]['consentVersion'],'2026-10-23')
 def test_mail_failure_keeps_fields_and_allows_retry_with_same_request_id(self):
  sent=[]
  def respond(route):
   p=route.request.post_data_json;sent.append(p)
   if len(sent)==1:route.fulfill(status=502,content_type='application/json',body=json.dumps({'ok':False,'message':'Почтовый сервер не принял заявку.'}))
   else:route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'requestId':p['requestId']}))
  self.page.route('**/api/request.php',respond);self.fill()
  self.page.locator('#mainForm button[type=submit]').click()
  self.page.wait_for_function('document.getElementById("mainFormStatus").textContent.includes("не принял")')
  self.assertEqual(self.page.locator('#mainForm [name=phone]').input_value(),'+7 (900) 123-45-67')
  self.assertNotIn('Заявка отправлена',self.page.locator('#mainFormStatus').inner_text())
  self.page.locator('#mainForm button[type=submit]').click()
  self.page.wait_for_function('document.getElementById("mainFormStatus").textContent.includes("Заявка отправлена")')
  self.assertEqual(sent[0]['requestId'],sent[1]['requestId'])
 def test_success_like_html_or_wrong_request_id_does_not_claim_delivery(self):
  self.page.route('**/api/request.php',lambda r:r.fulfill(status=200,content_type='text/html',body='ok'))
  self.fill();self.page.locator('#mainForm button[type=submit]').click()
  self.page.wait_for_function('document.getElementById("mainFormStatus").textContent.includes("Не удалось")')
  self.assertNotIn('Заявка отправлена',self.page.locator('#mainFormStatus').inner_text())
 def test_network_failure_is_readable_and_keeps_fields(self):
  self.page.route('**/api/request.php',lambda r:r.abort())
  self.fill();self.page.locator('#mainForm button[type=submit]').click()
  self.page.wait_for_function('document.getElementById("mainFormStatus").textContent.includes("Не удалось")')
  self.assertNotIn('Failed to fetch',self.page.locator('#mainFormStatus').inner_text())
  self.assertEqual(self.page.locator('#mainForm [name=name]').input_value(),'Татьяна')
  self.assertTrue(self.page.locator('#mainForm button[type=submit]').is_enabled())
 def test_github_pages_keeps_mail_draft_and_never_posts_to_php(self):
  from urllib.parse import urlparse
  import mimetypes
  root=Path(__file__).resolve().parent.parent
  posts=[]
  def local(route):
   path=urlparse(route.request.url).path.removeprefix('/mebelny-butik-48/') or 'index.html'
   if path.startswith('api/'):
    posts.append(path);route.abort();return
   file=root/path
   if file.is_file():route.fulfill(status=200,body=file.read_bytes(),content_type=mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
   else:route.fulfill(status=404,body='not found')
  self.context.route('https://stas5252.github.io/mebelny-butik-48/**',local)
  self.page.goto('https://stas5252.github.io/mebelny-butik-48/',wait_until='domcontentloaded')
  self.page.evaluate('window.contactSettings.requestsEnabled=true;window.refreshContactMode();')
  self.page.evaluate('()=>{window.openContactDraft=(url)=>{window.checkedDraft=url;};}')
  self.assertEqual(self.page.locator('#mainForm button[type=submit]').inner_text(),'Открыть письмо с заявкой')
  self.fill();self.page.locator('#mainForm button[type=submit]').click()
  self.assertTrue(self.page.evaluate('window.checkedDraft').startswith('mailto:mebelbutik.48@yandex.ru?'))
  self.assertEqual(posts,[])
 def test_missing_consent_does_not_contact_backend(self):
  sent=[];self.page.route('**/api/request.php',lambda r:sent.append(r.request.post_data))
  self.fill();self.page.locator('#mainForm [name=consent]').uncheck()
  self.page.locator('#mainForm button[type=submit]').click()
  self.assertIn('соглас',self.page.locator('#mainFormStatus').inner_text().lower());self.assertEqual(sent,[])

 def test_paused_public_form_cannot_send_even_when_submit_is_forced(self):
  self.page.reload(wait_until='domcontentloaded')
  sent=[];self.page.route('**/api/request.php',lambda r:sent.append(r.request.method))
  self.assertFalse(self.page.locator('#mainForm').is_visible())
  self.assertTrue(self.page.locator('#contactFallback').is_visible())
  self.assertTrue(self.page.locator('#mainForm [name=name]').is_disabled())
  self.page.evaluate('document.getElementById("mainForm").dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}))')
  self.assertEqual(sent,[])
  self.assertEqual(self.context.cookies(),[])
  self.assertEqual(self.page.evaluate('localStorage.length+sessionStorage.length'),0)

if __name__=='__main__':unittest.main(verbosity=2)
