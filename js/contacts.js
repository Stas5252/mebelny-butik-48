(function () {
  'use strict';
  var settings=window.contactSettings;
  var form=document.getElementById('mainForm');
  var fallback=document.getElementById('contactFallback');
  var description='';
  var emailPattern=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  function contactEmail(){return settings && emailPattern.test(settings.email) ? settings.email : '';}
  function scrollToContact(){
    var target=document.getElementById('cta');
    if(target) target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  }
  window.openContactDraft=function(url){ window.location.href=url; };
  window.prepareContactProject=function(text){
    description=String(text).slice(0,4000);
    var comment=form && form.elements.comment;
    if(comment) comment.value=description;
    var box=document.getElementById('projectSummary');
    var field=document.getElementById('projectText');
    if(field) field.value=description;
    if(box) box.hidden=false;
    scrollToContact();
  };
  function refreshContactMode(){
    var enabled=!!contactEmail();
    if(form) form.hidden=!enabled;
    if(fallback) fallback.hidden=enabled;
  }
  window.refreshContactMode=refreshContactMode;
  refreshContactMode();
  if(form){
    form.addEventListener('submit',function(event){
      event.preventDefault();
      var status=document.getElementById('mainFormStatus');
      function error(text,field){status.textContent=text;if(field){field.setAttribute('aria-invalid','true');field.focus();}}
      status.textContent='';
      var name=form.elements.name,phone=form.elements.phone,consent=form.elements.consent;
      [name,phone,consent].forEach(function(field){field.removeAttribute('aria-invalid');});
      if(!name.value.trim()){error('Укажите имя.',name);return;}
      if(!/^[78]\d{10}$/.test(phone.value.replace(/\D/g,''))){error('Укажите телефон РФ: 11 цифр, начиная с +7 или 8.',phone);return;}
      if(!consent.checked){error('Для подготовки письма подтвердите отдельное согласие на обработку данных.',consent);return;}
      var email=contactEmail();
      if(!email){error('Для обсуждения проекта позвоните по номеру +7 (904) 282-23-76.');return;}
      var body='Заявка на мебель\nИмя: '+name.value.trim()+'\nТелефон: '+phone.value.trim()+'\n\n'+form.elements.comment.value.trim()+
        '\n\nСогласие на обработку персональных данных для ответа на обращение: подтверждено.'+
        '\nРедакция согласия: '+settings.consentVersion+'.\nТекст: '+new URL('consent.html',location.href).href+
        '\nДата подготовки письма: '+new Date().toISOString();
      var url='mailto:'+email+'?subject='+encodeURIComponent('Заявка — Мебельный Бутик 48')+'&body='+encodeURIComponent(body);
      window.openContactDraft(url);
      status.textContent='Письмо подготовлено. Отправьте его в вашем почтовом приложении. Если приложение не открылось, позвоните нам.';
    });
    form.addEventListener('input',function(event){event.target.removeAttribute('aria-invalid');});
  }
  var download=document.getElementById('downloadProject');
  if(download) download.addEventListener('click',function(){
    if(!description) return;
    var blob=new Blob([description],{type:'text/plain;charset=utf-8'});
    var url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download='mebelny-butik-48-project.txt';document.body.appendChild(link);link.click();link.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
  });
  var mapButton=document.getElementById('loadMap');
  if(mapButton) mapButton.addEventListener('click',function(){
    var map=document.getElementById('map');
    var frame=document.createElement('iframe');
    frame.src='https://yandex.ru/map-widget/v1/?ll=39.531049%2C52.615507&z=17&mode=search&oid=193848899924&ol=biz';
    frame.title='Карта проезда: Липецк, Универсальный проезд, 9а';
    frame.allowFullscreen=true;frame.referrerPolicy='strict-origin-when-cross-origin';
    map.replaceChildren(frame);
  });
  if(location.hash.indexOf('#project=')===0){
    try{
      var project=decodeURIComponent(location.hash.slice(9));
      history.replaceState(null,'',location.pathname+location.search+'#cta');
      window.prepareContactProject(project);
    }catch(error){history.replaceState(null,'',location.pathname+location.search+'#cta');}
  }
})();
