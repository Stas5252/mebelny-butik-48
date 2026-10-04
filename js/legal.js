(function(){
'use strict';
var settings=window.contactSettings||{};
var operator=document.getElementById('legalOperator');
if(operator&&settings.legalName)operator.textContent=settings.legalName;
document.querySelectorAll('[data-setting]').forEach(function(element){var value=settings[element.dataset.setting];if(value)element.textContent=value;});
})();
