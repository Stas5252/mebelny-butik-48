<?php
declare(strict_types=1);
namespace MB48Requests;

function result(int $status, string $message, bool $ok = false, string $id = ''): array {
    return ['status'=>$status, 'body'=>['ok'=>$ok, 'message'=>$message, 'requestId'=>$id]];
}
function valid_text($value, int $max): bool {
    return is_string($value) && preg_match('//u', $value) === 1 && preg_match_all('/./us', $value) <= $max;
}
function handle_request(array $server, string $input, array $config, callable $send): array {
    if (($server['REQUEST_METHOD'] ?? '') !== 'POST') return result(405, 'Используйте форму заявки.');
    if (($config['accept_requests'] ?? false) !== true) return result(503, 'Онлайн-заявки временно недоступны. Позвоните в салон: +7 (904) 282-23-76.');
    $origin = parse_url($server['HTTP_ORIGIN'] ?? '');
    $host = strtolower($server['HTTP_HOST'] ?? '');
    $originHost = is_array($origin) ? strtolower($origin['host'] ?? '') . (isset($origin['port']) ? ':'.$origin['port'] : '') : '';
    if (!$host || $originHost !== $host || !in_array($origin['scheme'] ?? '', ['http','https'], true)) return result(403, 'Откройте форму на сайте салона.');
    if (strpos(strtolower($server['CONTENT_TYPE'] ?? ''), 'application/json') !== 0) return result(415, 'Неверный формат заявки.');
    if (strlen($input) > 32768) return result(413, 'Описание проекта слишком длинное.');
    try { $data = json_decode($input, true, 16, JSON_THROW_ON_ERROR); }
    catch (\Throwable $e) { return result(400, 'Не удалось прочитать заявку.'); }
    if (!is_array($data)) return result(400, 'Не удалось прочитать заявку.');
    $id = $data['requestId'] ?? '';
    if (!is_string($id) || !preg_match('/\A[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}\z/i', $id)) return result(422, 'Обновите страницу и повторите отправку.');
    if (!valid_text($data['name'] ?? null, 100) || !trim($data['name']) || preg_match('/[\x00-\x1f\x7f]/', $data['name'])) return result(422, 'Укажите имя.');
    if (!is_string($data['phone'] ?? null) || strlen($data['phone']) > 40) return result(422, 'Укажите телефон РФ.');
    $phone = preg_replace('/\D/', '', $data['phone']);
    if (!preg_match('/\A[78][0-9]{10}\z/', $phone)) return result(422, 'Укажите телефон РФ: 11 цифр, начиная с +7 или 8.');
    if (!valid_text($data['comment'] ?? '', 4000)) return result(422, 'Описание проекта слишком длинное.');
    if (($data['consent'] ?? false) !== true || ($data['consentVersion'] ?? '') !== '2026-10-23') return result(422, 'Подтвердите согласие на обработку данных.');
    if (!is_string($data['website'] ?? '') || ($data['website'] ?? '') !== '') return result(422, 'Не удалось отправить заявку.');
    $from = $config['mail_from'] ?? '';
    if (!filter_var($from, FILTER_VALIDATE_EMAIL) || preg_match('/[\r\n]/', $from)) return result(503, 'Отправка временно недоступна. Позвоните в салон.');
    $clean = ['name'=>trim($data['name']), 'phone'=>'+7'.substr($phone,1), 'comment'=>trim($data['comment'] ?? ''), 'consentVersion'=>'2026-10-23'];
    $fingerprint = hash('sha256', json_encode($clean, JSON_UNESCAPED_UNICODE));
    $file = $config['state_file'];
    $directory = dirname($file);
    if (!is_dir($directory) && !@mkdir($directory, 0700, true)) return result(503, 'Отправка временно недоступна.');
    if (is_link($file)) return result(503, 'Отправка временно недоступна.');
    $lock = @fopen($file, 'c+');
    if (!$lock) return result(503, 'Отправка временно недоступна.');
    @chmod($file, 0600);
    try {
        if (!flock($lock, LOCK_EX)) return result(503, 'Отправка временно недоступна.');
        $state = json_decode(stream_get_contents($lock), true) ?: ['requests'=>[], 'limits'=>[]];
        $now = time(); $cutoff = $now - ($config['rate_seconds'] ?? 3600);
        $state['requests'] = array_filter($state['requests'] ?? [], fn($r)=>$r['time'] > $cutoff);
        $state['limits'] = array_map(fn($t)=>array_values(array_filter($t, fn($v)=>$v > $cutoff)), $state['limits'] ?? []);
        $state['limits'] = array_filter($state['limits']);
        $key = hash('sha256', $id);
        if (isset($state['requests'][$key])) {
            if ($state['requests'][$key]['hash'] !== $fingerprint) return result(409, 'Изменённую заявку отправьте заново.');
            return result(200, 'Заявка отправлена. Мы свяжемся с вами.', true, $id);
        }
        $ip = hash('sha256', $server['REMOTE_ADDR'] ?? 'unknown');
        $attempts = $state['limits'][$ip] ?? [];
        if (count($attempts) >= ($config['rate_limit'] ?? 5)) return result(429, 'Слишком много попыток. Попробуйте позже или позвоните в салон.');
        if (count($state['requests']) >= 2000 || (count($state['limits']) >= 2000 && !isset($state['limits'][$ip]))) return result(503, 'Отправка временно недоступна. Позвоните в салон.');
        $attempts[] = $now; $state['limits'][$ip] = $attempts;
        $body = "Заявка с сайта «Мебельный Бутик 48»\n\nИмя: {$clean['name']}\nТелефон: {$clean['phone']}\n\nОписание проекта:\n{$clean['comment']}\n\nСогласие на обработку данных: подтверждено.\nРедакция: 2026-10-23\nТекст: {$server['HTTP_ORIGIN']}/consent.html\nДата: ".gmdate('c')."\nНомер заявки: {$id}\n";
        try { $accepted = $send('mebelbutik.48@yandex.ru', 'Новая заявка на мебель', $body, $from) === true; }
        catch (\Throwable $e) { $accepted = false; }
        if ($accepted) $state['requests'][$key] = ['hash'=>$fingerprint, 'time'=>$now];
        $encoded = json_encode($state);
        rewind($lock); ftruncate($lock,0);
        $written = fwrite($lock, $encoded); fflush($lock);
        if ($written !== strlen($encoded)) return result(503, 'Не удалось подтвердить отправку. Позвоните в салон.');
        return $accepted ? result(200, 'Заявка отправлена. Мы свяжемся с вами.', true, $id) : result(502, 'Почтовый сервер не принял заявку. Попробуйте позже или позвоните в салон.');
    } finally { flock($lock, LOCK_UN); fclose($lock); }
}
