<?php
header('Access-Control-Allow-Origin: *');
@setlocale(LC_ALL, 'C.UTF-8');

function safeShellArg($arg) {
    return "'" . str_replace("'", "'\\''", $arg) . "'";
}

// realpath()-resolved $path is only really "inside" $base when it equals $base
// or starts with "$base/" - a bare strpos($path, $base) === 0 check also lets
// a sibling directory through, e.g. resolved "/shares/Public-evil/x" would
// pass a check against base "/shares/Public" since the string itself matches
// as a prefix even though the directory is not a descendant.

// Security: Prevent path traversal and double URL encoding (%252e%252e, %00, null bytes)
function validateRelativePath($path) {
    if (!is_string($path)) return false;
    $decoded = rawurldecode($path);
    if (strpos($path, '..') !== false || strpos($path, "\0") !== false) return false;
    if (strpos($decoded, '..') !== false || strpos($decoded, "\0") !== false) return false;
    return true;
}

// 32-bit PHP integer overflow protection for large video files + combined stat syscall
function getSafeFileStat($fullPath) {
    $st = @stat($fullPath);
    if ($st === false) {
        $size = @filesize($fullPath);
        $mtime = @filemtime($fullPath);
        return array(
            'size' => ($size !== false && $size > 0) ? sprintf('%u', $size) : '0',
            'mtime' => ($mtime !== false) ? $mtime : 0
        );
    }
    $rawSize = $st['size'];
    $mtime = isset($st['mtime']) ? $st['mtime'] : 0;
    // In 32-bit PHP, sprintf('%u') accurately handles up to 4,294,967,295 bytes (4GB) with 0 shell forks.
    // Only if allocated filesystem blocks exceed 4GB (st_blocks * 512 > 4GB), shell out to stat command.
    if (isset($st['blocks']) && ($st['blocks'] * 512.0 > 4294967296.0)) {
        $cmd = 'export LC_ALL=C.UTF-8 && timeout 3 stat -c "%s" -- ' . safeShellArg($fullPath) . ' 2>/dev/null';
        $out = trim(@shell_exec($cmd));
        if ($out !== '' && ctype_digit($out)) {
            return array('size' => $out, 'mtime' => $mtime);
        }
    }
    return array('size' => sprintf('%u', $rawSize), 'mtime' => $mtime);
}

function getSafeFileSize($fullPath) {
    $st = getSafeFileStat($fullPath);
    return $st['size'];
}

function isWithinBaseDir($resolved, $base) {
    return $resolved === $base || strpos($resolved, $base . '/') === 0;
}

// WD My Cloud /shares/Public is a symlink to /DataVolume/shares/Public
$baseDir = realpath('/shares/Public');
if ($baseDir === false) {
    $baseDir = '/shares/Public';
}

$videoExts = array('mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v', 'flv', 'wmv', 'ts');
$subExts = array('smi', 'sami', 'srt', 'ass', 'ssa', 'vtt');
$ignoreList = array('.', '..', 'webplayer', 'incomplete', 'lost+found', '.DS_Store', 'Thumbs.db', 'desktop.ini', '.thumb');

// Helper: Make Apache Web URL from relative path with fast-path for clean ASCII paths
function makeWebUrl($relPath) {
    if (strpos($relPath, '\\') !== false) {
        $relPath = str_replace('\\', '/', $relPath);
    }
    $relPath = trim($relPath, '/');
    if ($relPath === '') return '/media/';
    // Fast path: if only safe URL path characters, skip explode and array_map
    if (!preg_match('/[^a-zA-Z0-9_\-\.\/]/', $relPath)) {
        return '/media/' . $relPath;
    }
    $parts = explode('/', $relPath);
    return '/media/' . implode('/', array_map('rawurlencode', $parts));
}

// Helper: Match subtitle basename to video basename without false-positive prefix matches (e.g. EP1 vs EP10)
function isMatchingSubtitleBase($subBase, $vidBase, $vLen = null) {
    if ($vLen === null) $vLen = strlen($vidBase);
    $sLen = strlen($subBase);
    if ($sLen === $vLen) return strcasecmp($subBase, $vidBase) === 0;
    if ($sLen < $vLen) return false;
    if (strncasecmp($subBase, $vidBase, $vLen) !== 0) return false;
    $nextChar = $subBase[$vLen];
    return ($nextChar === '.' || $nextChar === '_' || $nextChar === '-' || $nextChar === ' ' || $nextChar === '[' || $nextChar === '(');
}

// Helper: Format bytes - pure integer branch without log() / pow() (Item 9)
function formatBytes($bytes, $precision = 2) {
    $bytes = (float)$bytes;
    if ($bytes <= 0) return '0 B';
    if ($bytes < 1024) return $bytes . ' B';
    if ($bytes < 1048576) return round($bytes / 1024, $precision) . ' KB';
    if ($bytes < 1073741824) return round($bytes / 1048576, $precision) . ' MB';
    if ($bytes < 1099511627776) return round($bytes / 1073741824, $precision) . ' GB';
    return round($bytes / 1099511627776, $precision) . ' TB';
}

// -------------------------------------------------------------
// Action 1: Probe embedded subtitle streams in video (~0.5s)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'probe_subs') {
    header('Content-Type: application/json; charset=utf-8');
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    if (empty($videoRel) || !validateRelativePath($videoRel)) {
        echo json_encode(array('success' => false, 'error' => 'Invalid video path'));
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath) || is_link($fullVideoPath)) {
        echo json_encode(array('success' => false, 'error' => 'File not found'));
        exit;
    }
    
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (is_link($tmpDir)) {
        @unlink($tmpDir);
    }
    if (!is_dir($tmpDir)) {
        @mkdir($tmpDir, 0777, true);
    }
    $probeCacheFile = $tmpDir . '/probe_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath)) . '.json';
    if (file_exists($probeCacheFile) && filesize($probeCacheFile) > 0) {
        readfile($probeCacheFile);
        exit;
    }

    // 1. High-speed zero-disk pure Python MKV probe (< 0.05s vs 2.5s avconv)
    $fastCmd = 'timeout 5 python /shares/webplayer/stream_sub.py probe ' . safeShellArg($fullVideoPath) . ' 2>/dev/null';
    $fastOut = @shell_exec($fastCmd);
    if (!empty($fastOut)) {
        $fastJson = @json_decode($fastOut, true);
        if ($fastJson && isset($fastJson['success']) && $fastJson['success'] && isset($fastJson['subtitles'])) {
            @file_put_contents($probeCacheFile, $fastOut);
            echo $fastOut;
            exit;
        }
    }

    // 2. Fallback to avconv probe for non-MKV or unusual streams
    $cmd = 'export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && export LD_LIBRARY_PATH=/usr/local/wdmcserver/lib && timeout 8 /usr/local/wdmcserver/bin/avconv -probesize 65536 -analyzeduration 1000000 -i ' . safeShellArg($fullVideoPath) . ' 2>&1';
    $output = @shell_exec($cmd);
    
    $subs = array();
    $lines = explode("\n", $output);
    foreach ($lines as $line) {
        if (preg_match('/Stream #0[.:](\d+)(?:\(([^)]+)\))?: Subtitle: ([^,\n\r]+)/i', $line, $m)) {
            $s_id = $m[1];
            if (count($m) >= 4) {
                $lang = strtolower(trim($m[2]));
                $codec = strtolower(trim($m[3]));
            } else {
                $lang = 'und';
                $codec = isset($m[2]) ? strtolower(trim($m[2])) : 'srt';
            }
            if (empty($lang)) $lang = 'und';
            
            $langLabel = strtoupper($lang);
            if ($lang === 'kor' || $lang === 'ko' || $lang === 'korean') $langLabel = '한국어';
            else if ($lang === 'eng' || $lang === 'en' || $lang === 'english') $langLabel = '영어';
            else if ($lang === 'jpn' || $lang === 'ja' || $lang === 'japanese') $langLabel = '일본어';
            else if ($lang === 'chi' || $lang === 'zh' || $lang === 'chinese') $langLabel = '중국어';
            else if ($lang === 'fre' || $lang === 'fra' || $lang === 'fr') $langLabel = '프랑스어';
            else if ($lang === 'ger' || $lang === 'deu' || $lang === 'de') $langLabel = '독일어';
            else if ($lang === 'spa' || $lang === 'es') $langLabel = '스페인어';
            else if ($lang === 'rus' || $lang === 'ru') $langLabel = '러시아어';
            
            $isDef = stripos($line, '(default)') !== false;
            $isForced = stripos($line, '(forced)') !== false;
            
            $codecLabel = 'SRT';
            if (stripos($codec, 'ass') !== false || stripos($codec, 'ssa') !== false) {
                $codecLabel = 'ASS';
            }
            
            $label = '[내장-' . $langLabel . '] ' . $langLabel . ' 자막 (' . $codecLabel . ')';
            if ($isForced) $label .= ' [강제/일부]';
            else if ($isDef) $label .= ' [기본]';
            
            $subs[] = array(
                'stream_id' => $s_id,
                'lang' => $lang,
                'lang_label' => $langLabel,
                'label' => $label,
                'codec' => $codecLabel,
                'is_default' => $isDef,
                'is_forced' => $isForced,
                'embedded' => true
            );
        }
    }
    
    // Sort: Korean first, then English, then others; non-forced first
    usort($subs, function($a, $b) {
        $aKor = ($a['lang'] === 'kor' || $a['lang'] === 'ko') ? 0 : 1;
        $bKor = ($b['lang'] === 'kor' || $b['lang'] === 'ko') ? 0 : 1;
        if ($aKor !== $bKor) return $aKor - $bKor;
        
        $aForced = $a['is_forced'] ? 1 : 0;
        $bForced = $b['is_forced'] ? 1 : 0;
        if ($aForced !== $bForced) return $aForced - $bForced;
        
        return 0;
    });
    
    $respJson = json_encode(array('success' => true, 'subtitles' => $subs), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    @file_put_contents($probeCacheFile, $respJson);
    echo $respJson;
    exit;
}

// -------------------------------------------------------------
// Action 2: On-demand Zero-Disk Stream Subtitle directly to client
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'stream_sub') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    $streamId = isset($_GET['stream']) ? intval($_GET['stream']) : 0;
    $codec = isset($_GET['codec']) ? strtolower(trim($_GET['codec'])) : 'srt';
    if (!in_array($codec, array('srt', 'vtt', 'ass', 'ssa'), true)) {
        $codec = 'srt';
    }

    if (empty($videoRel) || !validateRelativePath($videoRel)) {
        header('HTTP/1.1 400 Bad Request');
        echo "Invalid video path";
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath) || is_link($fullVideoPath)) {
        header('HTTP/1.1 404 Not Found');
        echo "File not found";
        exit;
    }
    
    // Disable any output buffering for immediate progressive streaming
    if (function_exists('apache_setenv')) {
        @apache_setenv('no-gzip', '1');
    }
    @ini_set('zlib.output_compression', '0');
    @ini_set('implicit_flush', '1');
    while (ob_get_level()) {
        @ob_end_flush();
    }
    
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-cache, no-store, must-revalidate');
    header('Pragma: no-cache');
    header('Expires: 0');
    header('X-Accel-Buffering: no');
    
    // Volatile RAM cache in /tmp (tmpfs in RAM: 0 disk space on HDD, instant 2ms delivery)
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (is_link($tmpDir)) {
        @unlink($tmpDir);
    }
    if (!is_dir($tmpDir)) {
        @mkdir($tmpDir, 0777, true);
    }
    $cacheFile = $tmpDir . '/' . md5($fullVideoPath . ':' . $streamId . ':' . filemtime($fullVideoPath)) . '.' . $codec;
    if (file_exists($cacheFile) && filesize($cacheFile) > 0) {
        readfile($cacheFile);
        exit;
    }
    
    // Unified zero-disk high-speed stream with process supervision & orphan prevention
    $cmd = 'exec python /shares/webplayer/stream_sub.py ' . safeShellArg($fullVideoPath) . ' ' . $streamId;
    $descriptors = array(
        0 => array('pipe', 'r'),
        1 => array('pipe', 'w'),
        2 => array('file', '/dev/null', 'w')
    );
    $sysPath = getenv('PATH') ?: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
    $sysLd = getenv('LD_LIBRARY_PATH') ?: '/usr/local/wdmcserver/lib';
    $procEnv = array(
        'LANG' => 'C.UTF-8',
        'LC_ALL' => 'C.UTF-8',
        'PATH' => $sysPath,
        'LD_LIBRARY_PATH' => $sysLd
    );
    $proc = @proc_open($cmd, $descriptors, $pipes, null, $procEnv);
    $cacheFp = @fopen($cacheFile . '.tmp', 'wb');
    $timedOut = false;
    
    if (is_resource($proc)) {
        fclose($pipes[0]);
        stream_set_blocking($pipes[1], 1);
        stream_set_timeout($pipes[1], 15);
        
        while (!feof($pipes[1])) {
            if (connection_aborted()) {
                @proc_terminate($proc, 9);
                break;
            }
            $buffer = fread($pipes[1], 8192);
            $meta = stream_get_meta_data($pipes[1]);
            if ($meta['timed_out']) {
                $timedOut = true;
                @proc_terminate($proc, 9);
                break;
            }
            if ($buffer !== false && strlen($buffer) > 0) {
                echo $buffer;
                flush();
                if ($cacheFp) {
                    fwrite($cacheFp, $buffer);
                }
            }
        }
        fclose($pipes[1]);
        
        if (connection_aborted()) {
            @proc_terminate($proc, 9);
            @proc_close($proc);
            if ($cacheFp) {
                fclose($cacheFp);
                @unlink($cacheFile . '.tmp');
            }
            exit;
        }
        
        $exitCode = @proc_close($proc);
        if ($cacheFp) {
            fclose($cacheFp);
            if (!$timedOut && !connection_aborted() && $exitCode === 0 && file_exists($cacheFile . '.tmp') && filesize($cacheFile . '.tmp') > 0) {
                @rename($cacheFile . '.tmp', $cacheFile);
            } else {
                @unlink($cacheFile . '.tmp');
            }
        }
    }
    
    // Strict volatile RAM cache auto-prune (protect 226MB RAM)
    $now = time();
    $tmpFiles = @glob($tmpDir . '/*.tmp');
    if ($tmpFiles) {
        foreach ($tmpFiles as $tf) {
            if ($now - @filemtime($tf) > 120) {
                @unlink($tf);
            }
        }
    }
    $ramSubFiles = @glob($tmpDir . '/*.{srt,vtt,ass,ssa}', GLOB_BRACE);
    if ($ramSubFiles && count($ramSubFiles) > 15) {
        usort($ramSubFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
        while (count($ramSubFiles) > 10) {
            $old = array_shift($ramSubFiles);
            @unlink($old);
        }
    }
    $ramProbeFiles = @glob($tmpDir . '/probe_*.json');
    if ($ramProbeFiles && count($ramProbeFiles) > 80) {
        usort($ramProbeFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
        while (count($ramProbeFiles) > 60) {
            $old = array_shift($ramProbeFiles);
            @unlink($old);
        }
    }
    exit;
}

// -------------------------------------------------------------
// Helper: Load or generate keyframe-aligned HLS segment metadata (RAM cached)
// -------------------------------------------------------------
function getHlsInfo($fullVideoPath) {
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (is_link($tmpDir)) @unlink($tmpDir);
    if (!is_dir($tmpDir)) @mkdir($tmpDir, 0777, true);
    $cacheFile = $tmpDir . '/hls_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath)) . '.json';
    if (file_exists($cacheFile) && filesize($cacheFile) > 0) {
        $cached = @json_decode(@file_get_contents($cacheFile), true);
        if (is_array($cached) && !empty($cached['success'])) {
            return $cached;
        }
    }
    $cmd = 'timeout 5 python /shares/webplayer/stream_sub.py hls_info ' . safeShellArg($fullVideoPath) . ' 2>/dev/null';
    $out = @shell_exec($cmd);
    if (!empty($out)) {
        $parsed = @json_decode($out, true);
        if (is_array($parsed) && !empty($parsed['success']) && !empty($parsed['segments'])) {
            @file_put_contents($cacheFile, $out);
            $hlsFiles = @glob($tmpDir . '/hls_*.json');
            if ($hlsFiles && count($hlsFiles) > 40) {
                usort($hlsFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
                while (count($hlsFiles) > 30) {
                    @unlink(array_shift($hlsFiles));
                }
            }
            return $parsed;
        }
    }
    return array('success' => false, 'error' => 'HLS keyframe index unavailable');
}

// -------------------------------------------------------------
// Action 3: On-demand Virtual HLS Manifest (.m3u8) for MKV Remuxing
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_manifest') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    if (empty($videoRel) || !validateRelativePath($videoRel)) {
        header('HTTP/1.1 400 Bad Request');
        echo "Invalid video path";
        exit;
    }
    $rawPath = $baseDir . '/' . $videoRel;
    if (is_link($rawPath)) {
        header('HTTP/1.1 403 Forbidden');
        echo "Forbidden";
        exit;
    }
    $fullVideoPath = realpath($rawPath);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !is_file($fullVideoPath)) {
        header('HTTP/1.1 404 Not Found');
        echo "File not found";
        exit;
    }

    $info = getHlsInfo($fullVideoPath);
    if (empty($info['success']) || empty($info['segments'])) {
        header('HTTP/1.1 422 Unprocessable Entity');
        echo "HLS remuxing not supported for this file";
        exit;
    }

    $maxDur = 10;
    foreach ($info['segments'] as $seg) {
        if ($seg['dur'] > $maxDur) {
            $maxDur = (int)ceil($seg['dur']);
        }
    }

    header('Content-Type: application/vnd.apple.mpegurl; charset=utf-8');
    header('Cache-Control: private, max-age=300');

    $encodedVideo = rawurlencode($videoRel);
    echo "#EXTM3U\n";
    echo "#EXT-X-VERSION:3\n";
    echo "#EXT-X-TARGETDURATION:" . $maxDur . "\n";
    echo "#EXT-X-MEDIA-SEQUENCE:0\n";
    echo "#EXT-X-PLAYLIST-TYPE:VOD\n";

    foreach ($info['segments'] as $idx => $seg) {
        if ($idx > 0) {
            echo "#EXT-X-DISCONTINUITY\n";
        }
        echo sprintf("#EXTINF:%.3f,\n", (float)$seg['dur']);
        echo "api.php?action=hls_seg&video=" . $encodedVideo . "&i=" . $idx . "\n";
    }
    echo "#EXT-X-ENDLIST\n";
    exit;
}

// -------------------------------------------------------------
// Action 4: Zero-Disk On-Demand MPEG-TS Segment Remuxer (avconv -c copy)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_seg') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    $segIdx = isset($_GET['i']) ? intval($_GET['i']) : -1;
    if (empty($videoRel) || !validateRelativePath($videoRel) || $segIdx < 0) {
        header('HTTP/1.1 400 Bad Request');
        echo "Invalid parameters";
        exit;
    }
    $rawPath = $baseDir . '/' . $videoRel;
    if (is_link($rawPath)) {
        header('HTTP/1.1 403 Forbidden');
        echo "Forbidden";
        exit;
    }
    $fullVideoPath = realpath($rawPath);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !is_file($fullVideoPath)) {
        header('HTTP/1.1 404 Not Found');
        echo "File not found";
        exit;
    }

    $info = getHlsInfo($fullVideoPath);
    if (empty($info['success']) || !isset($info['segments'][$segIdx])) {
        header('HTTP/1.1 404 Not Found');
        echo "Segment not found";
        exit;
    }

    $seg = $info['segments'][$segIdx];
    $startSec = sprintf('%.3f', max(0.0, (float)$seg['start']));
    $durSec = sprintf('%.3f', max(0.2, (float)$seg['dur']));
    $vStream = isset($info['video_stream']) ? intval($info['video_stream']) : 0;
    $aStream = (isset($info['audio_stream']) && $info['audio_stream'] !== null) ? intval($info['audio_stream']) : -1;
    $vCodec = isset($info['video_codec']) ? strtolower($info['video_codec']) : '';

    if (function_exists('apache_setenv')) {
        @apache_setenv('no-gzip', '1');
    }
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level()) {
        @ob_end_clean();
    }

    header('Content-Type: video/mp2t');
    header('Cache-Control: private, max-age=300');
    header('X-Accel-Buffering: no');

    $mapArgs = '-map 0:' . $vStream;
    if ($aStream >= 0) {
        $mapArgs .= ' -map 0:' . $aStream;
    }
    $bsfArg = ($vCodec === 'h264') ? ' -bsf:v h264_mp4toannexb' : '';

    $cmd = 'exec /usr/local/wdmcserver/bin/avconv -ss ' . $startSec
        . ' -i ' . safeShellArg($fullVideoPath)
        . ' -t ' . $durSec
        . ' ' . $mapArgs
        . ' -c:v copy -c:a copy' . $bsfArg
        . ' -f mpegts pipe:1';

    $descriptors = array(
        0 => array('pipe', 'r'),
        1 => array('pipe', 'w'),
        2 => array('file', '/dev/null', 'w')
    );
    $sysPath = getenv('PATH') ?: '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';
    $procEnv = array(
        'LANG' => 'C.UTF-8',
        'LC_ALL' => 'C.UTF-8',
        'PATH' => $sysPath,
        'LD_LIBRARY_PATH' => '/usr/local/wdmcserver/lib'
    );

    $proc = @proc_open($cmd, $descriptors, $pipes, null, $procEnv);
    if (is_resource($proc)) {
        fclose($pipes[0]);
        stream_set_blocking($pipes[1], 1);
        stream_set_timeout($pipes[1], 20);
        while (!feof($pipes[1])) {
            if (connection_aborted()) {
                @proc_terminate($proc, 9);
                break;
            }
            $buf = fread($pipes[1], 32768);
            $meta = stream_get_meta_data($pipes[1]);
            if ($meta['timed_out']) {
                @proc_terminate($proc, 9);
                break;
            }
            if ($buf !== false && strlen($buf) > 0) {
                echo $buf;
                flush();
            }
        }
        fclose($pipes[1]);
        if (connection_aborted()) {
            @proc_terminate($proc, 9);
        }
        @proc_close($proc);
    }
    exit;
}

header('Content-Type: application/json; charset=utf-8');
$mode = isset($_GET['all']) && $_GET['all'] == '1' ? 'all' : 'folder';

if ($mode === 'all') {
    $allVideos = array();
    $allSubs = array();
    $baseMtime = @filemtime($baseDir);
    $maxMtime = ($baseMtime !== false) ? $baseMtime : 0;
    
    $scanRecursive = function($dir, $depth = 0) use (&$scanRecursive, &$allVideos, &$allSubs, &$maxMtime, $baseDir, $videoExts, $subExts, $ignoreList) {
        if ($depth > 8 || count($allVideos) >= 2500) return;
        $items = @scandir($dir);
        if ($items === false) return;
        
        foreach ($items as $item) {
            if (in_array($item, $ignoreList) || $item[0] === '.') continue;
            $fullPath = $dir . '/' . $item;
            
            if (is_link($fullPath)) continue;
            if (is_dir($fullPath)) {
                $dm = @filemtime($fullPath);
                if ($dm !== false && $dm > $maxMtime) $maxMtime = $dm;
                $scanRecursive($fullPath, $depth + 1);
            } else if (is_file($fullPath)) {
                $dotPos = strrpos($item, '.');
                if ($dotPos === false) continue;
                $ext = strtolower(substr($item, $dotPos + 1));
                $isVideo = in_array($ext, $videoExts, true);
                $isSub = in_array($ext, $subExts, true);
                if (!$isVideo && !$isSub) continue;
                
                $relPath = ltrim(substr($fullPath, strlen($baseDir)), '/\\');
                $folderRel = ltrim(substr($dir, strlen($baseDir)), '/\\');
                $baseName = substr($item, 0, $dotPos);
                
                if ($isVideo) {
                    $fstat = getSafeFileStat($fullPath);
                    $size = (float)$fstat['size'];
                    if ($size <= 0) continue;
                    $mtime = $fstat['mtime'];
                    if ($mtime !== false && $mtime > $maxMtime) $maxMtime = $mtime;
                    $allVideos[] = array(
                        'name' => $item,
                        'basename' => $baseName,
                        'ext' => $ext,
                        'folder' => $folderRel,
                        'rel_path' => $relPath,
                        'url' => makeWebUrl($relPath),
                        'size' => $size,
                        'size_formatted' => formatBytes($size),
                        'mtime' => $mtime,
                        'mtime_formatted' => date('Y-m-d', $mtime),
                        'subtitles' => array()
                    );
                } else {
                    $mtime = @filemtime($fullPath);
                    if ($mtime !== false && $mtime > $maxMtime) $maxMtime = $mtime;
                    $allSubs[] = array(
                        'filename' => $item,
                        'basename' => $baseName,
                        'ext' => $ext,
                        'folder' => $folderRel,
                        'rel_path' => $relPath,
                        'url' => makeWebUrl($relPath)
                    );
                }
            }
        }
    };
    
    $scanRecursive($baseDir);

    // Group subs by folder first so each video only scans its own folder's
    // subs instead of every sub in the whole library (was O(videos * subs) -
    // on a big flat collection that's millions of comparisons on a 650MHz CPU).
    $subsByFolder = array();
    foreach ($allSubs as $sub) {
        $subsByFolder[$sub['folder']][] = $sub;
    }

    foreach ($allVideos as &$video) {
        if (!isset($subsByFolder[$video['folder']])) continue;
        $vidBase = $video['basename'];
        $vLen = strlen($vidBase);
        foreach ($subsByFolder[$video['folder']] as $sub) {
            $subBase = $sub['basename'];
            if (isMatchingSubtitleBase($subBase, $vidBase, $vLen)) {
                $video['subtitles'][] = $sub;
            }
        }
    }
    unset($video);
    
    usort($allVideos, function($a, $b) {
        return strnatcasecmp($a['name'], $b['name']);
    });
    
    $etag = '"' . md5($baseDir . ':' . $maxMtime . ':' . count($allVideos) . ':' . count($allSubs)) . '"';
    header('ETag: ' . $etag);
    $clientEtag = isset($_SERVER['HTTP_IF_NONE_MATCH']) ? trim($_SERVER['HTTP_IF_NONE_MATCH']) : '';
    if (strpos($clientEtag, 'W/') === 0) {
        $clientEtag = substr($clientEtag, 2);
    }
    if ($clientEtag === $etag) {
        header('HTTP/1.1 304 Not Modified');
        exit;
    }

    echo json_encode(array(
        'success' => true,
        'mode' => 'all',
        'current_dir' => '',
        'parent_dir' => null,
        'dirs' => array(),
        'videos' => $allVideos,
        'count' => count($allVideos)
    ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);
    exit;
}

// Mode: Folder navigation
$requestDir = isset($_GET['dir']) ? trim($_GET['dir'], " /\\") : '';
$targetDir = $baseDir;

if ($requestDir !== '') {
    if (!validateRelativePath($requestDir)) {
        echo json_encode(array('success' => false, 'error' => 'Path traversal prohibited'));
        exit;
    }
    $resolved = realpath($baseDir . '/' . $requestDir);
    if ($resolved !== false && isWithinBaseDir($resolved, $baseDir) && is_dir($resolved) && !is_link($resolved)) {
        $targetDir = $resolved;
    } else {
        echo json_encode(array('success' => false, 'error' => 'Invalid directory path'));
        exit;
    }
}

// Compute parent dir
$parentDir = null;
if ($requestDir !== '') {
    $parent = dirname($requestDir);
    $parentDir = ($parent === '.' || $parent === '/' || $parent === '') ? '' : $parent;
}

$items = @scandir($targetDir);
if ($items === false) {
    echo json_encode(array('success' => false, 'error' => 'Cannot read directory'));
    exit;
}

$subtitlesMap = array();
$rawVideos = array();
$rawDirs = array();
$targetMtime = @filemtime($targetDir);
$maxFolderMtime = ($targetMtime !== false) ? $targetMtime : 0;

foreach ($items as $item) {
    if (in_array($item, $ignoreList) || $item[0] === '.') continue;
    $fullPath = $targetDir . '/' . $item;
    if (is_link($fullPath)) continue;
    
    if (is_dir($fullPath)) {
        $dm = @filemtime($fullPath);
        if ($dm !== false && $dm > $maxFolderMtime) {
            $maxFolderMtime = $dm;
        }
        $rawDirs[] = $item;
    } else if (is_file($fullPath)) {
        $dotPos = strrpos($item, '.');
        if ($dotPos === false) continue;
        $ext = strtolower(substr($item, $dotPos + 1));
        if (in_array($ext, $videoExts, true)) {
            $rawVideos[] = array('item' => $item, 'ext' => $ext, 'baseName' => substr($item, 0, $dotPos), 'fullPath' => $fullPath);
        } else if (in_array($ext, $subExts, true)) {
            $sm = @filemtime($fullPath);
            if ($sm !== false && $sm > $maxFolderMtime) {
                $maxFolderMtime = $sm;
            }
            $baseName = substr($item, 0, $dotPos);
            $subRel = ($requestDir ? $requestDir . '/' : '') . $item;
            $subtitlesMap[$item] = array(
                'filename' => $item,
                'basename' => $baseName,
                'ext' => $ext,
                'path' => $subRel,
                'url' => makeWebUrl($subRel)
            );
        }
    }
}

$dirs = array();
// OPT-4: Cap per-folder scandir calls. If there are many subdirs, skipping the
// count is cheaper than doing N extra scandir() calls on a slow HDD NAS.
$scanSubdirCounts = count($rawDirs) <= 30;
foreach ($rawDirs as $d) {
    $dRel = ($requestDir ? $requestDir . '/' : '') . $d;
    $dFull = $targetDir . '/' . $d;
    
    $vidCount = 0;
    $subDirCount = 0;
    if ($scanSubdirCounts) {
        $subItems = @scandir($dFull);
        if ($subItems !== false) {
            foreach ($subItems as $si) {
                if ($si[0] === '.' || in_array($si, $ignoreList)) continue;
                $dotPos = strrpos($si, '.');
                if ($dotPos !== false) {
                    $siExt = strtolower(substr($si, $dotPos + 1));
                    if (in_array($siExt, $videoExts)) {
                        $vidCount++;
                        continue;
                    }
                }
                if (is_dir($dFull . '/' . $si)) {
                    $subDirCount++;
                }
            }
        }
    }
    
    $dirs[] = array(
        'name' => $d,
        'rel_path' => $dRel,
        'video_count' => $vidCount,
        'subdir_count' => $subDirCount
    );
}

$videos = array();
$hasSubs = !empty($subtitlesMap);
foreach ($rawVideos as $rv) {
    $item = $rv['item'];
    $ext = $rv['ext'];
    $baseName = $rv['baseName'];
    $fullPath = $rv['fullPath'];
    
    $fstat = getSafeFileStat($fullPath);
    $size = (float)$fstat['size'];
    if ($size <= 0) continue;
    $mtime = $fstat['mtime'];
    if ($mtime !== false && $mtime > $maxFolderMtime) {
        $maxFolderMtime = $mtime;
    }
    
    $matchedSubs = array();
    if ($hasSubs) {
        $vLen = strlen($baseName);
        foreach ($subtitlesMap as $subItem => $subInfo) {
            if (isMatchingSubtitleBase($subInfo['basename'], $baseName, $vLen)) {
                $matchedSubs[] = $subInfo;
            }
        }
    }
    
    $relPath = ($requestDir ? $requestDir . '/' : '') . $item;
    $webUrl = makeWebUrl($relPath);
    
    $videos[] = array(
        'name' => $item,
        'basename' => $baseName,
        'ext' => $ext,
        'rel_path' => $relPath,
        'folder' => $requestDir,
        'url' => $webUrl,
        'size' => $size,
        'size_formatted' => formatBytes($size),
        'mtime' => $mtime,
        'mtime_formatted' => date('Y-m-d', $mtime),
        'subtitles' => $matchedSubs
    );
}

usort($dirs, function($a, $b) {
    return strnatcasecmp($a['name'], $b['name']);
});

usort($videos, function($a, $b) {
    return strnatcasecmp($a['name'], $b['name']);
});

$etag = '"' . md5($targetDir . ':' . $maxFolderMtime . ':' . count($items)) . '"';
header('ETag: ' . $etag);
$clientEtag = isset($_SERVER['HTTP_IF_NONE_MATCH']) ? trim($_SERVER['HTTP_IF_NONE_MATCH']) : '';
if (strpos($clientEtag, 'W/') === 0) {
    $clientEtag = substr($clientEtag, 2);
}
if ($clientEtag === $etag) {
    header('HTTP/1.1 304 Not Modified');
    exit;
}

echo json_encode(array(
    'success' => true,
    'mode' => 'folder',
    'current_dir' => $requestDir,
    'parent_dir' => $parentDir,
    'dirs' => $dirs,
    'videos' => $videos,
    'count' => count($videos)
), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR);
