(function () {
  'use strict';
  var settings=window.contactSettings;
  var form=document.getElementById('mainForm');
  var fallback=document.getElementById('contactFallback');
  var description='';
  var contactDraft='';
  var sending=false;
  var requestId='';
  var emailPattern=/^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  function contactEmail(){
    var email=settings && String(settings.email || '').trim();
    return emailPattern.test(email) && !/@(?:[^@]+\.)?invalid$/i.test(email) ? email : '';
  }
  function requestEndpoint(){
    if(location.protocol==='http:' && !/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) return '';
    if(!contactEmail() || !settings.requestEndpoint || /(^|\.)github\.io$/i.test(location.hostname) || !/^https?:$/.test(location.protocol)) return '';
    try{var url=new URL(settings.requestEndpoint,location.href);return url.origin===location.origin?url.href:'';}catch(error){return '';}
  }
  function newRequestId(){
    if(crypto.randomUUID) return crypto.randomUUID();
    var bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
    var hex=Array.from(bytes,function(n){return n.toString(16).padStart(2,'0');}).join('');
    return hex.slice(0,8)+'-'+hex.slice(8,12)+'-'+hex.slice(12,16)+'-'+hex.slice(16,20)+'-'+hex.slice(20);
  }
  function saveText(text,filename){
    var blob=new Blob([text],{type:'text/plain;charset=utf-8'});
    var url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }
  function scrollToContact(){
    var target=document.getElementById('cta');
    if(target) target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});
  }
  window.openContactDraft=function(url){ window.location.href=url; };
  window.prepareContactProject=function(text){
    if(sending){scrollToContact();return;}
    requestId='';
    description=String(text).slice(0,4000);
    contactDraft='';
    document.getElementById('downloadContactDraft').hidden=true;
    document.getElementById('mainFormStatus').textContent='';
    var comment=form && form.elements.comment;
    if(comment) comment.value=description;
    var box=document.getElementById('projectSummary');
    var field=document.getElementById('projectText');
    if(field) field.value=description;
    if(box) box.hidden=false;
    scrollToContact();
  };
  function refreshContactMode(){
    var email=contactEmail(),enabled=!!email;
    var emailLink=document.getElementById('contactEmailLink');
    if(emailLink){
      emailLink.hidden=!enabled;
      emailLink.textContent=email;
      emailLink.href=enabled?'mailto:'+email:'';
    }
    if(form){
      form.hidden=false;
      form.querySelector('[type="submit"]').textContent=requestEndpoint()?'Отправить заявку':enabled?'Открыть письмо с заявкой':'Подготовить заявку';
    }
    if(fallback) fallback.hidden=enabled;
    document.getElementById('contactConsentIntro').textContent=enabled?'Даю ':'Ознакомился с ';
    document.getElementById('contactConsentLink').textContent=enabled?'согласие на обработку персональных данных':'проектом согласия на обработку персональных данных';
    document.getElementById('contactConsentPurpose').textContent=enabled?' для ответа на моё обращение.':'. Сейчас данные не отправляются.';
    var help=document.getElementById('contactEmailHelp');
    if(help) help.textContent=requestEndpoint()?
      'Заявка будет отправлена на '+email+'. Если отправить не получится, данные останутся в форме — можно повторить попытку или позвонить нам.':enabled?
      'Откроется ваше почтовое приложение с заполненным письмом на '+email+'. Чтобы направить заявку, нажмите «Отправить» в почте. Если приложение не открылось, сохраните черновик и отправьте его на этот адрес через свою почту.':
      'Приём заявок по email пока не настроен. Здесь можно подготовить и сохранить черновик на своё устройство. Сайт не отправляет введённые данные. Для заказа замера позвоните нам.';
  }
  window.refreshContactMode=refreshContactMode;
  refreshContactMode();
  if(form){
    form.addEventListener('submit',async function(event){
      event.preventDefault();
      if(sending) return;
      var status=document.getElementById('mainFormStatus');
      function error(text,field){status.textContent=text;if(field){field.setAttribute('aria-invalid','true');field.focus();}}
      status.textContent='';
      contactDraft='';
      document.getElementById('downloadContactDraft').hidden=true;
      var name=form.elements.name,phone=form.elements.phone,consent=form.elements.consent;
      [name,phone,consent].forEach(function(field){field.removeAttribute('aria-invalid');});
      if(!name.value.trim()){error('Укажите имя.',name);return;}
      if(!/^[78]\d{10}$/.test(phone.value.replace(/\D/g,''))){error('Укажите телефон РФ: 11 цифр, начиная с +7 или 8.',phone);return;}
      if(!consent.checked){error(contactEmail()?'Подтвердите отдельное согласие на обработку данных.':'Ознакомьтесь с проектом согласия и отметьте галочку для подготовки локального черновика.',consent);return;}
      var email=contactEmail();
      var body='Заявка на мебель\nИмя: '+name.value.trim()+'\nТелефон: '+phone.value.trim()+'\n\n'+form.elements.comment.value.trim()+
        (email?'\n\nСогласие на обработку персональных данных для ответа на обращение: подтверждено.':'\n\nЛокальный черновик. Получатель не настроен; временные документы необходимо дополнить. Ознакомление с проектом согласия: отмечено.')+
        '\nРедакция согласия: '+settings.consentVersion+'.\nТекст: '+new URL('consent.html',location.href).href+
        '\nДата подготовки письма: '+new Date().toISOString();
      contactDraft=(email?'Кому: '+email+'\nТема: Заявка — Мебельный Бутик 48\n\n':'')+body;
      document.getElementById('downloadContactDraft').hidden=false;
      if(!email){
        status.textContent='Черновик подготовлен на вашем устройстве. Заявка не отправлена: email получателя пока не настроен. Сохраните черновик или позвоните нам.';
        return;
      }
      var endpoint=requestEndpoint();
      if(endpoint){
        if(!requestId) requestId=newRequestId();
        var payload={requestId:requestId,name:name.value.trim(),phone:phone.value.trim(),comment:form.elements.comment.value.trim(),consent:consent.checked,consentVersion:settings.consentVersion,website:form.elements.website?form.elements.website.value:''};
        sending=true;form.setAttribute('aria-busy','true');
        var fields=Array.from(form.elements),disabled=fields.map(function(field){return field.disabled;});
        fields.forEach(function(field){field.disabled=true;});
        var submit=form.querySelector('[type="submit"]');submit.textContent='Отправляем…';
        status.textContent='Отправляем заявку…';
        var controller=new AbortController(),timer=setTimeout(function(){controller.abort();},20000);
        try{
          var response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'omit',redirect:'error',cache:'no-store',signal:controller.signal,body:JSON.stringify(payload)});
          var answer=await response.json();
          if(!response.ok) throw new Error(answer.message || 'Не удалось отправить заявку. Попробуйте позже или позвоните нам.');
          if(answer.ok!==true || answer.requestId!==payload.requestId) throw new Error('Не удалось подтвердить отправку. Попробуйте ещё раз или позвоните нам.');
          status.textContent='Заявка отправлена на '+email+'. Мы свяжемся с вами.';
        }catch(error){
          status.textContent=error.name==='AbortError'?'Не удалось подтвердить отправку. Данные сохранены в форме; попробуйте ещё раз или позвоните нам.':(error instanceof SyntaxError || error instanceof TypeError)?'Не удалось отправить заявку. Данные сохранены в форме; попробуйте позже или позвоните нам.':error.message || 'Не удалось отправить заявку. Попробуйте позже или позвоните нам.';
        }finally{
          clearTimeout(timer);sending=false;form.removeAttribute('aria-busy');
          fields.forEach(function(field,i){field.disabled=disabled[i];});refreshContactMode();
        }
        return;
      }
      var url='mailto:'+email+'?subject='+encodeURIComponent('Заявка — Мебельный Бутик 48')+'&body='+encodeURIComponent(body);
      window.openContactDraft(url);
      status.textContent='Письмо подготовлено. Отправьте его в вашем почтовом приложении. Если приложение не открылось, сохраните черновик и отправьте его на '+email+' через свою почту.';
    });
    form.addEventListener('input',function(event){
      if(sending) return;
      requestId='';
      event.target.removeAttribute('aria-invalid');
      contactDraft='';
      document.getElementById('downloadContactDraft').hidden=true;
      document.getElementById('mainFormStatus').textContent='';
    });
  }
  var download=document.getElementById('downloadProject');
  if(download) download.addEventListener('click',function(){
    if(!description) return;
    saveText(description,'mebelny-butik-48-project.txt');
  });
  var draftDownload=document.getElementById('downloadContactDraft');
  if(draftDownload) draftDownload.addEventListener('click',function(){
    if(contactDraft) saveText(contactDraft,'mebelny-butik-48-request.txt');
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
