<?php
$lib = __DIR__ . '/../api/request-lib.php';
if (!is_file($lib)) { fwrite(STDERR, "FAIL: request handler is missing\n"); exit(1); }
require $lib;
function check($condition, $message) { if (!$condition) throw new RuntimeException($message); }
function payload($id = '11111111-1111-4111-8111-111111111111') {
    return ['requestId'=>$id, 'name'=>'Татьяна', 'phone'=>'+7 (900) 123-45-67', 'comment'=>'Кухня & остров, 270 см', 'consent'=>true, 'consentVersion'=>'2026-10-23', 'website'=>''];
}
$server = ['REQUEST_METHOD'=>'POST','CONTENT_TYPE'=>'application/json','HTTP_HOST'=>'example.test','HTTP_ORIGIN'=>'https://example.test','HTTPS'=>'on','REMOTE_ADDR'=>'192.0.2.5'];
$state = sys_get_temp_dir() . '/mb48-test-' . bin2hex(random_bytes(8)) . '.json';
$config = ['accept_requests'=>true,'state_file'=>$state,'mail_from'=>'site@example.test','rate_limit'=>3,'rate_seconds'=>3600];
$sent=[];
$mailer=function($to,$subject,$body,$from) use (&$sent) { $sent[]=compact('to','subject','body','from'); return true; };
function run_case($data, $server, $config, $mailer) { return \MB48Requests\handle_request($server, json_encode($data, JSON_UNESCAPED_UNICODE), $config, $mailer); }
try {
    $paused=$config;$paused['accept_requests']=false;
    check(run_case(payload(),$server,$paused,$mailer)['status']===503,'paused endpoint accepted contact data');
    check(count($sent)===0 && !is_file($state),'paused endpoint sent mail or wrote request state');
    $missing=$config;unset($missing['accept_requests']);
    check(run_case(payload(),$server,$missing,$mailer)['status']===503,'missing explicit enable accepted a request');
    $bad=payload();$bad['consent']=false;
    check(run_case($bad,$server,$config,$mailer)['status']===422,'missing consent accepted');
    $bad=payload();$bad['phone']='123';
    check(run_case($bad,$server,$config,$mailer)['status']===422,'invalid phone accepted');
    $bad=payload();$bad['website']='spam';
    check(run_case($bad,$server,$config,$mailer)['status']===422,'honeypot accepted');
    $bad=payload();$bad['consentVersion']='old';
    check(run_case($bad,$server,$config,$mailer)['status']===422,'stale consent accepted');
    $other=$server;$other['HTTP_ORIGIN']='https://other.test';
    check(run_case(payload(),$other,$config,$mailer)['status']===403,'foreign origin accepted');
    $other=$server;$other['REQUEST_METHOD']='GET';
    check(run_case(payload(),$other,$config,$mailer)['status']===405,'GET accepted');
    check(count($sent)===0,'invalid submissions sent mail');
    $good=payload();$good['to']='attacker@example.test';
    $result=run_case($good,$server,$config,$mailer);
    check($result['status']===200 && $result['body']['ok']===true,'valid request failed');
    check($sent[0]['to']==='mebelbutik.48@yandex.ru','recipient was changed by input');
    check(str_contains($sent[0]['body'],'Татьяна') && str_contains($sent[0]['body'],'Кухня & остров'),'data missing from email');
    check(str_contains($sent[0]['body'],'2026-10-23'),'consent evidence missing');
    check(run_case($good,$server,$config,$mailer)['body']['ok']===true && count($sent)===1,'duplicate sent twice');
    $changed=$good;$changed['comment']='Другой проект';
    check(run_case($changed,$server,$config,$mailer)['status']===409,'changed request reused token');
    $failed=payload('22222222-2222-4222-8222-222222222222');
    $result=run_case($failed,$server,$config,fn()=>false);
    check($result['status']===502 && $result['body']['ok']===false,'mail failure claimed success');
    check(run_case($failed,$server,$config,$mailer)['body']['ok']===true,'failed request could not be retried');
    check(run_case(payload('33333333-3333-4333-8333-333333333333'),$server,$config,$mailer)['status']===429,'rate limit not enforced');
    $stored=file_get_contents($state);
    check(!str_contains($stored,'Татьяна') && !str_contains($stored,'Кухня') && !str_contains($stored,'192.0.2.5'),'contact data persisted in limiter');
    echo "PASS: validation, consent, origin, recipient, duplicate prevention, failures, retry and rate limit\n";
} finally { if (is_file($state)) unlink($state); }
