<?php
declare(strict_types=1);
require __DIR__ . '/request-lib.php';
header('Content-Type: application/json; charset=UTF-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
$host = strtolower((string)parse_url('http://'.($_SERVER['SERVER_NAME'] ?? ''), PHP_URL_HOST));
$from = getenv('MB48_MAIL_FROM') ?: (strpos($host,'.') !== false && !filter_var($host,FILTER_VALIDATE_IP) ? 'no-reply@'.preg_replace('/^www\./','',$host) : '');
$config = [
    'mail_from'=>$from,
    'state_file'=>rtrim(sys_get_temp_dir(), DIRECTORY_SEPARATOR).'/mb48-'.substr(hash('sha256',__DIR__),0,16).'/requests.json',
    'rate_limit'=>5,
    'rate_seconds'=>3600
];
$sender = function(string $to, string $subject, string $body, string $from): bool {
    if (!function_exists('mail')) return false;
    $headers = [
        'MIME-Version'=>'1.0',
        'Content-Type'=>'text/plain; charset=UTF-8',
        'Content-Transfer-Encoding'=>'base64',
        'From'=>'=?UTF-8?B?'.base64_encode('Мебельный Бутик 48').'?= <'.$from.'>'
    ];
    return @mail($to, '=?UTF-8?B?'.base64_encode($subject).'?=', chunk_split(base64_encode($body),76,"\r\n"), $headers);
};
try {
    $input = file_get_contents('php://input', false, null, 0, 32769);
    $response = \MB48Requests\handle_request($_SERVER, $input === false ? '' : $input, $config, $sender);
} catch (Throwable $e) { $response = \MB48Requests\result(503, 'Отправка временно недоступна. Позвоните в салон.'); }
http_response_code($response['status']);
if ($response['status']===405) header('Allow: POST');
if ($response['status']===429) header('Retry-After: 3600');
echo json_encode($response['body'], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
