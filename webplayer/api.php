<?php
if (PHP_SAPI !== 'cli') {
    header('Access-Control-Allow-Origin: *');
}
@setlocale(LC_ALL, 'C.UTF-8');
if (file_exists(__DIR__ . '/fmp4_muxer.php')) {
    require_once __DIR__ . '/fmp4_muxer.php';
}

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
// Action 0: Font Folder Browser & On-Demand Font Index for JASSUB (libass WASM)
// -------------------------------------------------------------
function extractFontFamilyNames($filePath) {
    $names = array();
    $base = basename($filePath);
    $dot = strrpos($base, '.');
    $stem = ($dot !== false) ? substr($base, 0, $dot) : $base;
    $ext = ($dot !== false) ? strtolower(substr($base, $dot + 1)) : '';
    if ($stem !== '') {
        $names[] = $stem;
    }
    // Pure-PHP lightweight TTF/OTF/TTC 'name' table parser (reads only header + name table)
    if (!in_array($ext, array('ttf', 'otf', 'ttc'), true)) {
        return $names;
    }
    $fp = @fopen($filePath, 'rb');
    if (!$fp) return $names;
    $hdr = @fread($fp, 12);
    if ($hdr === false || strlen($hdr) < 12) {
        fclose($fp);
        return $names;
    }
    $offsets = array(0);
    if (substr($hdr, 0, 4) === 'ttcf') {
        $numFontsArr = unpack('N', substr($hdr, 8, 4));
        $numFonts = min(isset($numFontsArr[1]) ? (int)$numFontsArr[1] : 0, 8);
        if ($numFonts > 0) {
            $offBytes = @fread($fp, $numFonts * 4);
            if ($offBytes !== false && strlen($offBytes) === $numFonts * 4) {
                $offsets = array_values(unpack('N*', $offBytes));
            }
        }
    }
    foreach ($offsets as $fontOff) {
        if (@fseek($fp, $fontOff, SEEK_SET) !== 0) continue;
        $sfnt = @fread($fp, 12);
        if ($sfnt === false || strlen($sfnt) < 12) continue;
        $ntArr = unpack('n', substr($sfnt, 4, 2));
        $numTables = isset($ntArr[1]) ? (int)$ntArr[1] : 0;
        if ($numTables <= 0 || $numTables > 128) continue;
        $dirBytes = @fread($fp, $numTables * 16);
        if ($dirBytes === false || strlen($dirBytes) < $numTables * 16) continue;
        $nameOffset = 0;
        $nameLength = 0;
        for ($i = 0; $i < $numTables; $i++) {
            $tag = substr($dirBytes, $i * 16, 4);
            if ($tag === 'name') {
                $tbl = unpack('Noff/Nlen', substr($dirBytes, $i * 16 + 8, 8));
                $nameOffset = (int)$tbl['off'];
                $nameLength = (int)$tbl['len'];
                break;
            }
        }
        if ($nameOffset <= 0 || $nameLength < 6 || $nameLength > 262144) continue;
        if (@fseek($fp, $nameOffset, SEEK_SET) !== 0) continue;
        $nameData = @fread($fp, $nameLength);
        if ($nameData === false || strlen($nameData) < 6) continue;
        $nh = unpack('nfmt/ncnt/nstrOff', substr($nameData, 0, 6));
        $cnt = min((int)$nh['cnt'], 500);
        $strOff = (int)$nh['strOff'];
        for ($r = 0; $r < $cnt; $r++) {
            $recPos = 6 + $r * 12;
            if ($recPos + 12 > strlen($nameData)) break;
            $rec = unpack('npid/neid/nlid/nnid/nlen/noff', substr($nameData, $recPos, 12));
            // nameID 1=Font Family, 4=Full Name, 16=Typographic Family
            if (!in_array($rec['nid'], array(1, 4, 16), true)) continue;
            $sPos = $strOff + $rec['off'];
            $sLen = $rec['len'];
            if ($sPos < 0 || $sLen <= 0 || $sPos + $sLen > strlen($nameData)) continue;
            $raw = substr($nameData, $sPos, $sLen);
            $decoded = '';
            if ($rec['pid'] === 3 || $rec['pid'] === 0) {
                // Windows/Unicode UTF-16BE
                $conv = @iconv('UTF-16BE', 'UTF-8//IGNORE', $raw);
                if ($conv !== false) $decoded = trim($conv);
            } elseif ($rec['pid'] === 1 && $rec['eid'] === 0) {
                $decoded = trim($raw);
            }
            if ($decoded !== '' && !in_array($decoded, $names, true)) {
                $names[] = $decoded;
            }
        }
    }
    fclose($fp);
    return $names;
}

if (isset($_GET['action']) && $_GET['action'] === 'font_dirs') {
    header('Content-Type: application/json; charset=utf-8');
    $parentRel = isset($_GET['parent']) ? trim(str_replace('\\', '/', $_GET['parent']), '/') : '';
    if ($parentRel !== '' && !validateRelativePath($parentRel)) {
        echo json_encode(array('success' => false, 'error' => 'Invalid path'));
        exit;
    }
    $targetDir = ($parentRel !== '') ? realpath($baseDir . '/' . $parentRel) : $baseDir;
    if ($targetDir === false || !is_dir($targetDir) || !isWithinBaseDir($targetDir, $baseDir)) {
        echo json_encode(array('success' => false, 'error' => 'Directory not found'));
        exit;
    }
    $fontExts = array('ttf', 'otf', 'ttc', 'woff2', 'woff');
    $folders = array();
    $curFontCount = 0;
    $entries = @scandir($targetDir);
    if ($entries !== false) {
        foreach ($entries as $e) {
            if ($e === '.' || $e === '..' || $e[0] === '.' || in_array($e, $ignoreList, true)) continue;
            $full = $targetDir . '/' . $e;
            if (is_link($full)) continue;
            if (is_dir($full)) {
                $subFonts = 0;
                $hasSubDirs = false;
                $subEntries = @scandir($full);
                if ($subEntries !== false) {
                    foreach ($subEntries as $se) {
                        if ($se === '.' || $se === '..' || $se[0] === '.') continue;
                        $sf = $full . '/' . $se;
                        if (is_link($sf)) continue;
                        if (is_dir($sf)) {
                            $hasSubDirs = true;
                        } else {
                            $dp = strrpos($se, '.');
                            $ext = ($dp !== false) ? strtolower(substr($se, $dp + 1)) : '';
                            if (in_array($ext, $fontExts, true)) $subFonts++;
                        }
                    }
                }
                $relItem = ($parentRel !== '' ? $parentRel . '/' : '') . $e;
                $folders[] = array(
                    'name' => $e,
                    'rel_path' => $relItem,
                    'font_count' => $subFonts,
                    'has_children' => $hasSubDirs
                );
            } else {
                $dp = strrpos($e, '.');
                $ext = ($dp !== false) ? strtolower(substr($e, $dp + 1)) : '';
                if (in_array($ext, $fontExts, true)) $curFontCount++;
            }
        }
    }
    usort($folders, function($a, $b) {
        if ($a['font_count'] !== $b['font_count']) return $b['font_count'] - $a['font_count'];
        return strnatcasecmp($a['name'], $b['name']);
    });
    echo json_encode(array(
        'success' => true,
        'parent' => $parentRel,
        'current_font_count' => $curFontCount,
        'folders' => $folders
    ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if (isset($_GET['action']) && $_GET['action'] === 'font_index') {
    header('Content-Type: application/json; charset=utf-8');
    $rawFolders = isset($_GET['folders']) ? $_GET['folders'] : array();
    if (is_string($rawFolders)) {
        $rawFolders = ($rawFolders !== '') ? explode('|', $rawFolders) : array();
    }
    if (!is_array($rawFolders)) $rawFolders = array();
    $rawFolders = array_slice(array_unique($rawFolders), 0, 20);

    $fontExts = array('ttf', 'otf', 'ttc', 'woff2', 'woff');
    $availableFonts = array();
    $folderStats = array();
    $allFontsList = array();

    foreach ($rawFolders as $relF) {
        $relF = trim(str_replace('\\', '/', (string)$relF), '/');
        if ($relF !== '' && !validateRelativePath($relF)) continue;
        $dirFull = ($relF !== '') ? realpath($baseDir . '/' . $relF) : $baseDir;
        if ($dirFull === false || !is_dir($dirFull) || !isWithinBaseDir($dirFull, $baseDir)) {
            $folderStats[$relF] = array('exists' => false, 'count' => 0, 'fonts' => array());
            continue;
        }
        $entries = @scandir($dirFull);
        $fList = array();
        if ($entries !== false) {
            foreach ($entries as $e) {
                if (count($fList) >= 150) break;
                if ($e === '.' || $e === '..' || $e[0] === '.') continue;
                $full = $dirFull . '/' . $e;
                if (!is_file($full) || is_link($full)) continue;
                $dp = strrpos($e, '.');
                $ext = ($dp !== false) ? strtolower(substr($e, $dp + 1)) : '';
                if (!in_array($ext, $fontExts, true)) continue;
                $itemRel = ($relF !== '' ? $relF . '/' : '') . $e;
                $url = makeWebUrl($itemRel);
                $names = extractFontFamilyNames($full);
                $primaryName = !empty($names) ? $names[0] : $e;
                foreach ($names as $nm) {
                    $key = function_exists('mb_strtolower') ? mb_strtolower($nm, 'UTF-8') : strtolower($nm);
                    if ($key !== '' && !isset($availableFonts[$key])) {
                        $availableFonts[$key] = $url;
                    }
                }
                $sz = (float)getSafeFileSize($full);
                $entryObj = array(
                    'name' => $primaryName,
                    'aliases' => $names,
                    'file' => $e,
                    'rel_path' => $itemRel,
                    'url' => $url,
                    'size_formatted' => formatBytes($sz, 1)
                );
                $fList[] = $entryObj;
                $allFontsList[] = $entryObj;
            }
        }
        $folderStats[$relF] = array('exists' => true, 'count' => count($fList), 'fonts' => $fList);
    }

    echo json_encode(array(
        'success' => true,
        'available_fonts' => $availableFonts,
        'folder_stats' => $folderStats,
        'fonts' => $allFontsList
    ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
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
    
    // Sort: Korean first, then English, then others; non-forced first (stable tie-break on PHP 5.6)
    foreach ($subs as $si => &$subRef) {
        $subRef['_idx'] = $si;
    }
    unset($subRef);
    usort($subs, function($a, $b) {
        $aKor = ($a['lang'] === 'kor' || $a['lang'] === 'ko') ? 0 : 1;
        $bKor = ($b['lang'] === 'kor' || $b['lang'] === 'ko') ? 0 : 1;
        if ($aKor !== $bKor) return $aKor - $bKor;
        
        $aForced = $a['is_forced'] ? 1 : 0;
        $bForced = $b['is_forced'] ? 1 : 0;
        if ($aForced !== $bForced) return $aForced - $bForced;
        
        return $a['_idx'] - $b['_idx'];
    });
    foreach ($subs as &$subRef) {
        unset($subRef['_idx']);
    }
    unset($subRef);
    
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
    $cacheFile = $tmpDir . '/hls_v3_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath)) . '.json';
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

// Fast in-process 33-bit MPEG-TS PCR/PTS/DTS shifter (5x faster than spawning Python,
// 32-bit ARM PHP float-safe with 53-bit exact mantissa, byte-for-byte identical).
function shiftTsPts33(&$buf, $pos, $off90k) {
    $b0 = ord($buf[$pos]);
    $b1 = ord($buf[$pos + 1]);
    $b2 = ord($buf[$pos + 2]);
    $b3 = ord($buf[$pos + 3]);
    $b4 = ord($buf[$pos + 4]);
    $val = ((($b0 >> 1) & 0x07) * 1073741824.0)
         + ($b1 * 4194304.0)
         + ((($b2 >> 1) & 0x7F) * 32768.0)
         + ($b3 * 128.0)
         + (($b4 >> 1) & 0x7F);
    $val = fmod($val + $off90k, 8589934592.0);
    if ($val < 0.0) $val += 8589934592.0;
    $hi = (int)floor($val / 1073741824.0);
    $rInt = (int)($val - ($hi * 1073741824.0));
    $buf[$pos]     = chr(($b0 & 0xF1) | (($hi & 0x07) << 1));
    $buf[$pos + 1] = chr(($rInt >> 22) & 0xFF);
    $buf[$pos + 2] = chr(((($rInt >> 15) & 0x7F) << 1) | 0x01);
    $buf[$pos + 3] = chr(($rInt >> 7) & 0xFF);
    $buf[$pos + 4] = chr((($rInt & 0x7F) << 1) | 0x01);
}

function shiftTsPcr33(&$buf, $p, $off90k) {
    $p0 = ord($buf[$p]);
    $p1 = ord($buf[$p + 1]);
    $p2 = ord($buf[$p + 2]);
    $p3 = ord($buf[$p + 3]);
    $p4 = ord($buf[$p + 4]);
    $pcr = ($p0 * 33554432.0) + ($p1 * 131072.0) + ($p2 * 512.0) + ($p3 * 2.0) + ($p4 >> 7);
    $pcr = fmod($pcr + $off90k, 8589934592.0);
    if ($pcr < 0.0) $pcr += 8589934592.0;
    $b0 = (int)floor($pcr / 33554432.0);
    $rem = (int)($pcr - ($b0 * 33554432.0));
    $buf[$p]     = chr($b0 & 0xFF);
    $buf[$p + 1] = chr(($rem >> 17) & 0xFF);
    $buf[$p + 2] = chr(($rem >> 9) & 0xFF);
    $buf[$p + 3] = chr(($rem >> 1) & 0xFF);
    $buf[$p + 4] = chr((($rem & 1) << 7) | ($p4 & 0x7F));
}

function shiftTsFileInPlace($tsPath, $offsetSec) {
    $off90k = fmod(round($offsetSec * 90000.0), 8589934592.0);
    if ($off90k == 0.0) return true;
    $data = @file_get_contents($tsPath);
    if ($data === false) return false;
    $n = strlen($data);
    if ($n < 188) return true;
    $limit = $n - 187;
    for ($off = 0; $off < $limit; $off += 188) {
        if ($data[$off] !== "\x47") {
            $nextSync = strpos($data, "\x47", $off + 1);
            if ($nextSync === false) break;
            $off = $nextSync - 188;
            continue;
        }
        // Fast string bitmask check skips >99% of video payload packets with zero ord() calls
        if (($data[$off + 1] & "\x40") === "\x00" && ($data[$off + 3] & "\x20") === "\x00") {
            continue;
        }
        $b1 = ord($data[$off + 1]);
        $b3 = ord($data[$off + 3]);
        $idx = $off + 4;
        if (($b3 & 0x20) !== 0) {
            $afLen = ord($data[$idx]);
            if ($afLen >= 7 && ($idx + 6 < $off + 188) && (ord($data[$idx + 1]) & 0x10) !== 0) {
                shiftTsPcr33($data, $idx + 2, $off90k);
            }
            $idx += 1 + $afLen;
        }
        if (($b1 & 0x40) !== 0 && ($b3 & 0x10) !== 0 && $idx + 14 <= $off + 188) {
            if ($data[$idx] === "\x00" && $data[$idx + 1] === "\x00" && $data[$idx + 2] === "\x01") {
                $pf = ord($data[$idx + 7]) & 0xC0;
                if ($pf === 0x80) {
                    shiftTsPts33($data, $idx + 9, $off90k);
                } elseif ($pf === 0xC0 && $idx + 19 <= $off + 188) {
                    shiftTsPts33($data, $idx + 9, $off90k);
                    shiftTsPts33($data, $idx + 14, $off90k);
                }
            }
        }
    }
    return (@file_put_contents($tsPath, $data) !== false);
}

function getHlsSegCachePath($fullVideoPath, $segIdx) {
    return '/tmp/webplayer_sub_ram/hseg_v3_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath)) . '_' . intval($segIdx) . '.ts';
}

function buildHlsSegment($fullVideoPath, $info, $segIdx) {
    if (!isset($info['segments'][$segIdx])) return false;
    $seg = $info['segments'][$segIdx];
    $isLastSeg = ($segIdx >= count($info['segments']) - 1);
    $startSec = (float)$seg['start'];
    $durSec = (float)$seg['dur'];
    $startSecStr = sprintf('%.3f', max(0.0, $startSec));
    // Trim 10ms off non-final segment duration so avconv -t stops cleanly before
    // the next segment's IDR keyframe (prevents duplicate boundary frames on 24/30/60fps MKVs).
    $cutDurSec = max(0.2, $durSec - 0.010);
    $durArg = $isLastSeg ? '' : (' -t ' . sprintf('%.3f', $cutDurSec));
    $vStream = isset($info['video_stream']) ? intval($info['video_stream']) : 0;
    $aCodec = isset($info['audio_codec']) ? strtolower($info['audio_codec']) : '';
    $aStream = (isset($info['audio_stream']) && $info['audio_stream'] !== null && in_array($aCodec, array('aac', 'mp3', 'ac3', 'eac3')))
        ? intval($info['audio_stream'])
        : -1;
    $vCodec = isset($info['video_codec']) ? strtolower($info['video_codec']) : '';

    $tmpDir = '/tmp/webplayer_sub_ram';
    if (is_link($tmpDir)) @unlink($tmpDir);
    if (!is_dir($tmpDir)) @mkdir($tmpDir, 0777, true);

    $segCacheFile = getHlsSegCachePath($fullVideoPath, $segIdx);
    if (file_exists($segCacheFile) && filesize($segCacheFile) > 0) {
        return $segCacheFile;
    }

    $lockFile = $tmpDir . '/hseg_remux.lock';
    $lockFp = @fopen($lockFile, 'cb');
    if ($lockFp) {
        @flock($lockFp, LOCK_EX);
    }
    $ok = false;
    if (file_exists($segCacheFile) && filesize($segCacheFile) > 0) {
        $ok = true;
    } else {
        $tmpSegFile = $segCacheFile . '.' . getmypid() . '.tmp';
        $mapArgs = '-map 0:' . $vStream;
        if ($aStream >= 0) {
            $mapArgs .= ' -map 0:' . $aStream;
        }
        $bsfArg = ($vCodec === 'h264') ? ' -bsf:v h264_mp4toannexb' : '';
        $cmd = 'export LANG=C.UTF-8 LC_ALL=C.UTF-8 LD_LIBRARY_PATH=/usr/local/wdmcserver/lib && timeout 15 /usr/local/wdmcserver/bin/avconv -y -probesize 65536 -analyzeduration 0 -ss '
            . $startSecStr
            . ' -i ' . safeShellArg($fullVideoPath)
            . $durArg
            . ' ' . $mapArgs
            . ' -c:v copy -c:a copy' . $bsfArg
            . ' -f mpegts ' . safeShellArg($tmpSegFile) . ' 2>/dev/null';
        $outLines = array();
        $ret = 0;
        @exec($cmd, $outLines, $ret);
        if ($ret === 0 && file_exists($tmpSegFile) && filesize($tmpSegFile) > 0) {
            if ($startSec > 0.001) {
                shiftTsFileInPlace($tmpSegFile, $startSec);
            }
            if (@rename($tmpSegFile, $segCacheFile)) {
                $ok = true;
            } else {
                @unlink($tmpSegFile);
            }
        } else {
            @unlink($tmpSegFile);
        }

        // Prune stale .tmp files (>60s) and cap RAM cache to 5 recent segments (~12-16MB max in tmpfs)
        $now = time();
        $staleTmps = @glob($tmpDir . '/hseg_*.tmp');
        if ($staleTmps) {
            foreach ($staleTmps as $tf) {
                if ($now - @filemtime($tf) > 60) @unlink($tf);
            }
        }
        $segFiles = @glob($tmpDir . '/hseg_*.ts');
        if ($segFiles && count($segFiles) > 5) {
            usort($segFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
            while (count($segFiles) > 5) {
                @unlink(array_shift($segFiles));
            }
        }
    }
    if ($lockFp) {
        @flock($lockFp, LOCK_UN);
        @fclose($lockFp);
    }
    return $ok ? $segCacheFile : false;
}

// Detached non-blocking 1-segment lookahead prefetch: runs AT MOST 1 background
// avconv job across the entire NAS (enforced by flock -n) while current segment transmits.
function spawnHlsPrefetch($fullVideoPath, $segIdx) {
    $segIdx = intval($segIdx);
    if ($segIdx < 0) return;
    $nextFile = getHlsSegCachePath($fullVideoPath, $segIdx);
    if (file_exists($nextFile) && filesize($nextFile) > 0) return;
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (!is_dir($tmpDir)) @mkdir($tmpDir, 0777, true);
    $cmd = 'nohup /usr/bin/flock -n ' . escapeshellarg($tmpDir . '/hseg_prefetch.lock')
        . ' timeout 15 php /shares/webplayer/api.php --prefetch '
        . safeShellArg($fullVideoPath) . ' ' . $segIdx
        . ' </dev/null >/dev/null 2>&1 &';
    @exec($cmd);
}

// CLI mode: background lookahead prefetch worker
if (PHP_SAPI === 'cli' && isset($argv[1]) && $argv[1] === '--prefetch') {
    if (isset($argv[2]) && isset($argv[3])) {
        $rawTarget = $argv[2];
        $idxTarget = intval($argv[3]);
        if (!is_link($rawTarget)) {
            $resolvedTarget = realpath($rawTarget);
            if ($resolvedTarget !== false && isWithinBaseDir($resolvedTarget, $baseDir) && is_file($resolvedTarget)) {
                $pInfo = getHlsInfo($resolvedTarget);
                if (!empty($pInfo['success']) && isset($pInfo['segments'][$idxTarget])) {
                    buildHlsSegment($resolvedTarget, $pInfo, $idxTarget);
                }
            }
        }
    }
    exit(0);
}

// -------------------------------------------------------------
// Helper: Serve an in-memory buffer with exact Content-Length,
// Accept-Ranges: bytes, HTTP 206 Partial Content, and optional gzip
// -------------------------------------------------------------
function serveMemoryResponse($body, $contentType, $cacheControl, $allowGzip = false) {
    if (function_exists('apache_setenv')) @apache_setenv('no-gzip', '1');
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level()) @ob_end_clean();

    header('Content-Type: ' . $contentType);
    header('Accept-Ranges: bytes');
    header('Cache-Control: ' . $cacheControl);

    $totalSize = strlen($body);
    if (isset($_SERVER['HTTP_RANGE']) && preg_match('/^bytes=\s*(\d*)-(\d*)$/i', trim($_SERVER['HTTP_RANGE']), $rm)) {
        $start = 0;
        $end = $totalSize - 1;
        if ($rm[1] !== '' && $rm[2] !== '') {
            $start = (int)$rm[1];
            $end = min($totalSize - 1, (int)$rm[2]);
        } elseif ($rm[1] !== '') {
            $start = (int)$rm[1];
        } elseif ($rm[2] !== '') {
            $start = max(0, $totalSize - (int)$rm[2]);
        }
        if ($start > $end || $start >= $totalSize) {
            header('HTTP/1.1 416 Requested Range Not Satisfiable');
            header('Content-Range: bytes */' . $totalSize);
            exit;
        }
        header('HTTP/1.1 206 Partial Content');
        header('Content-Range: bytes ' . $start . '-' . $end . '/' . $totalSize);
        header('Content-Length: ' . ($end - $start + 1));
        echo substr($body, $start, $end - $start + 1);
        exit;
    }

    if ($allowGzip && $totalSize > 1024 && function_exists('gzencode')
        && isset($_SERVER['HTTP_ACCEPT_ENCODING']) && stripos($_SERVER['HTTP_ACCEPT_ENCODING'], 'gzip') !== false) {
        $gz = @gzencode($body, 1);
        if ($gz !== false) {
            header('Content-Encoding: gzip');
            header('Vary: Accept-Encoding');
            header('Content-Length: ' . strlen($gz));
            echo $gz;
            exit;
        }
    }

    header('Content-Length: ' . $totalSize);
    echo $body;
    exit;
}

// -------------------------------------------------------------
// Helpers: Native Apple HLS WebVTT Subtitle Engine
// (Converts external SMI/SRT/ASS/VTT & embedded MKV ASS/SRT to UTF-8 WebVTT
//  for iOS Safari AVPlayerViewController native fullscreen & CC menu!)
// -------------------------------------------------------------
function decodeSubtitleToUtf8($raw) {
    if ($raw === '' || $raw === false) return '';
    $len = strlen($raw);
    if ($len >= 2 && $raw[0] === "\xFF" && $raw[1] === "\xFE") {
        $conv = @iconv('UTF-16LE', 'UTF-8//IGNORE', substr($raw, 2));
        return ($conv !== false) ? $conv : $raw;
    }
    if ($len >= 2 && $raw[0] === "\xFE" && $raw[1] === "\xFF") {
        $conv = @iconv('UTF-16BE', 'UTF-8//IGNORE', substr($raw, 2));
        return ($conv !== false) ? $conv : $raw;
    }
    if ($len >= 3 && $raw[0] === "\xEF" && $raw[1] === "\xBB" && $raw[2] === "\xBF") {
        return substr($raw, 3);
    }
    if (preg_match('//u', $raw)) {
        return $raw;
    }
    $conv = @iconv('CP949', 'UTF-8//IGNORE', $raw);
    if ($conv !== false && $conv !== '') return $conv;
    $conv2 = @iconv('EUC-KR', 'UTF-8//IGNORE', $raw);
    return ($conv2 !== false && $conv2 !== '') ? $conv2 : $raw;
}

function formatVttTimestamp($sec) {
    if (!is_finite($sec) || $sec < 0.0) $sec = 0.0;
    $totalMs = (int)round($sec * 1000.0);
    $ms = $totalMs % 1000;
    $totalSec = (int)floor($totalMs / 1000);
    $s = $totalSec % 60;
    $totalMin = (int)floor($totalSec / 60);
    $m = $totalMin % 60;
    $h = (int)floor($totalMin / 60);
    return sprintf('%02d:%02d:%02d.%03d', $h, $m, $s, $ms);
}

function cleanVttLineText($txt) {
    $txt = html_entity_decode($txt, ENT_QUOTES | ENT_HTML401, 'UTF-8');
    $txt = str_replace("\xC2\xA0", ' ', $txt); // NBSP -> space
    $txt = str_replace("\r\n", "\n", $txt);
    $txt = str_replace("\r", "\n", $txt);
    $lines = explode("\n", $txt);
    $out = array();
    foreach ($lines as $ln) {
        $ln = trim(preg_replace('/[ \t]+/', ' ', $ln));
        if ($ln !== '') $out[] = $ln;
    }
    $joined = implode("\n", $out);
    if ($joined === '') return '';
    // Escape WebVTT markup characters in dialogue text
    return str_replace(array('&', '<', '>'), array('&amp;', '&lt;', '&gt;'), $joined);
}

function parseClockTimeToSec($str) {
    $str = trim($str);
    if (!preg_match('/^(?:(\d+):)?(\d{1,2}):(\d{1,2})(?:[.,](\d{1,3}))?/', $str, $m)) return -1.0;
    $h = ($m[1] !== '') ? (int)$m[1] : 0;
    $min = (int)$m[2];
    $sec = (int)$m[3];
    $msStr = isset($m[4]) ? str_pad($m[4], 3, '0') : '000';
    return $h * 3600.0 + $min * 60.0 + $sec + ((int)$msStr) / 1000.0;
}

function convertSubContentToVtt($rawBytes, $ext, $mpegtsOffset = -1, $syncOffset = 0.0) {
    $text = decodeSubtitleToUtf8($rawBytes);
    $ext = strtolower($ext);
    $cues = array(); // each: array(start, end, text)

    if ($ext === 'smi' || $ext === 'sami') {
        $text = preg_replace('/<!--.*?-->/s', '', $text);
        if (preg_match_all('/<SYNC\b[^>]*\bStart\s*=\s*["\']?(-?\d+)["\']?[^>]*>(.*?)(?=<SYNC\b|<\/BODY|<\/SAMI|$)/is', $text, $matches, PREG_SET_ORDER)) {
            $rawItems = array();
            foreach ($matches as $m) {
                $startSec = ((float)$m[1]) / 1000.0;
                $body = $m[2];
                $body = preg_replace('/<br\s*\/?>/i', "\n", $body);
                $body = preg_replace('/<\/p\s*>/i', "\n", $body);
                $body = strip_tags($body);
                $clean = cleanVttLineText($body);
                $rawItems[] = array($startSec, $clean);
            }
            $n = count($rawItems);
            for ($i = 0; $i < $n; $i++) {
                $st = $rawItems[$i][0];
                $txt = $rawItems[$i][1];
                if ($txt === '') continue;
                // Look ahead for the next strictly later SYNC timestamp (handles bilingual/simultaneous cues)
                $en = $st + 5.0;
                for ($j = $i + 1; $j < $n; $j++) {
                    if ($rawItems[$j][0] > $st + 0.01) {
                        $en = $rawItems[$j][0];
                        break;
                    }
                }
                if ($en <= $st + 0.05) $en = $st + 3.0;
                if ($en - $st > 15.0) $en = $st + 10.0;
                $cues[] = array($st, $en, $txt);
            }
        }
    } elseif ($ext === 'ass' || $ext === 'ssa') {
        $lines = preg_split('/\r\n|\r|\n/', $text);
        $textIdx = 9;
        $startIdx = 1;
        $endIdx = 2;
        foreach ($lines as $ln) {
            if (stripos($ln, 'Format:') === 0 && stripos($ln, 'Text') !== false && stripos($ln, 'Start') !== false) {
                $cols = array_map('trim', explode(',', substr($ln, 7)));
                foreach ($cols as $ci => $cn) {
                    $cl = strtolower($cn);
                    if ($cl === 'start') $startIdx = $ci;
                    elseif ($cl === 'end') $endIdx = $ci;
                    elseif ($cl === 'text') $textIdx = $ci;
                }
            } elseif (stripos($ln, 'Dialogue:') === 0) {
                $parts = explode(',', substr($ln, 9), $textIdx + 1);
                if (count($parts) > $textIdx) {
                    $st = parseClockTimeToSec($parts[$startIdx]);
                    $en = parseClockTimeToSec($parts[$endIdx]);
                    if ($st >= 0.0 && $en > $st) {
                        $body = $parts[$textIdx];
                        // Skip ASS vector drawing commands ({\p1}...{\p0})
                        if (preg_match('/\\\\p[1-9]/', $body)) continue;
                        $body = preg_replace('/\{[^}]*\}/', '', $body);
                        $body = str_replace(array('\\N', '\\n', '\\h'), array("\n", "\n", ' '), $body);
                        $clean = cleanVttLineText($body);
                        if ($clean !== '') {
                            $cues[] = array($st, $en, $clean);
                        }
                    }
                }
            }
        }
    } else {
        // SRT or WebVTT
        $blocks = preg_split('/\r?\n[ \t]*\r?\n/', trim($text));
        foreach ($blocks as $blk) {
            $trimmedBlk = trim($blk);
            if ($trimmedBlk === '' || preg_match('/^(?:WEBVTT|STYLE|NOTE)\b/i', $trimmedBlk)) continue;
            $lines = preg_split('/\r?\n/', $trimmedBlk);
            if (count($lines) < 2) continue;
            $timeLineIdx = -1;
            foreach ($lines as $li => $l) {
                if (strpos($l, '-->') !== false) {
                    $timeLineIdx = $li;
                    break;
                }
            }
            if ($timeLineIdx === -1) continue;
            $tParts = explode('-->', $lines[$timeLineIdx]);
            if (count($tParts) < 2) continue;
            $st = parseClockTimeToSec($tParts[0]);
            $en = parseClockTimeToSec($tParts[1]);
            if ($st < 0.0 || $en <= $st) continue;
            $bodyLines = array_slice($lines, $timeLineIdx + 1);
            $body = implode("\n", $bodyLines);
            $body = preg_replace('/<br\s*\/?>/i', "\n", $body);
            $body = preg_replace('/\{[^}]*\}/', '', $body);
            $body = strip_tags($body);
            $clean = cleanVttLineText($body);
            if ($clean !== '') {
                $cues[] = array($st, $en, $clean);
            }
        }
    }

    usort($cues, function($a, $b) {
        if ($a[0] == $b[0]) return ($a[1] < $b[1]) ? -1 : 1;
        return ($a[0] < $b[0]) ? -1 : 1;
    });

    $vtt = "WEBVTT\n";
    if ($mpegtsOffset >= 0) {
        $vtt .= "X-TIMESTAMP-MAP=MPEGTS:" . intval($mpegtsOffset) . ",LOCAL:00:00:00.000\n";
    }
    $vtt .= "\n";

    $cueIdx = 1;
    $seenCue = array();
    foreach ($cues as $c) {
        $st = max(0.0, $c[0] + $syncOffset);
        $en = max($st + 0.1, $c[1] + $syncOffset);
        $tsStart = formatVttTimestamp($st);
        $tsEnd = formatVttTimestamp($en);
        $dedupKey = $tsStart . '|' . $tsEnd . '|' . $c[2];
        if (isset($seenCue[$dedupKey])) continue;
        $seenCue[$dedupKey] = true;
        $vtt .= $cueIdx . "\n" . $tsStart . " --> " . $tsEnd . "\n" . $c[2] . "\n\n";
        $cueIdx++;
    }
    return $vtt;
}

function normalizeIsoLang2($lang, $label = '') {
    $l = strtolower(trim((string)$lang));
    if (in_array($l, array('kor', 'ko', 'korean'))) return 'ko';
    if (in_array($l, array('eng', 'en', 'english'))) return 'en';
    if (in_array($l, array('jpn', 'ja', 'japanese'))) return 'ja';
    if (in_array($l, array('chi', 'zho', 'zh', 'chinese'))) return 'zh';
    if (strlen($l) === 2 && ctype_alpha($l)) return $l;
    $lbl = strtolower((string)$label);
    if (strpos($lbl, '한국어') !== false || strpos($lbl, 'kor') !== false) return 'ko';
    if (strpos($lbl, 'english') !== false || strpos($lbl, '영어') !== false) return 'en';
    if (strpos($lbl, '일본어') !== false || strpos($lbl, 'jpn') !== false) return 'ja';
    return 'und';
}

function collectHlsSubtitleTracks($fullVideoPath, $videoRel, $baseDir) {
    global $subExts;
    $tracks = array();
    $dir = dirname($fullVideoPath);
    $vidBase = pathinfo($fullVideoPath, PATHINFO_FILENAME);
    $vLen = strlen($vidBase);
    $relDir = dirname($videoRel);
    if ($relDir === '.' || $relDir === '/' || $relDir === '\\') $relDir = '';

    // 1. External matching subtitle files in the same folder
    $items = @scandir($dir);
    if ($items !== false) {
        foreach ($items as $item) {
            if ($item === '.' || $item === '..') continue;
            $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
            if (!in_array($ext, $subExts)) continue;
            $subBase = pathinfo($item, PATHINFO_FILENAME);
            if (!isMatchingSubtitleBase($subBase, $vidBase, $vLen)) continue;
            $subFull = $dir . '/' . $item;
            if (!is_file($subFull) || is_link($subFull)) continue;
            $subRel = ($relDir !== '' ? ($relDir . '/') : '') . $item;
            $low = strtolower($item);
            $lang = 'ko';
            if (strpos($low, '.en.') !== false || strpos($low, '_en.') !== false || strpos($low, '.eng.') !== false) $lang = 'en';
            elseif (strpos($low, '.jp.') !== false || strpos($low, '.jpn.') !== false || strpos($low, '.ja.') !== false) $lang = 'ja';
            $tracks[] = array(
                'type' => 'ext',
                'name' => '외부 ' . strtoupper($ext) . ' 자막',
                'lang' => $lang,
                'sub_rel' => $subRel,
                'is_kor' => ($lang === 'ko') ? 0 : 1,
                'is_forced' => 0,
                'orig_idx' => count($tracks)
            );
        }
    }

    // 2. Embedded MKV subtitle tracks (cached via probe_*.json, < 10ms)
    $extVid = strtolower(pathinfo($fullVideoPath, PATHINFO_EXTENSION));
    if ($extVid === 'mkv') {
        $tmpDir = '/tmp/webplayer_sub_ram';
        if (!is_dir($tmpDir)) @mkdir($tmpDir, 0777, true);
        $probeCache = $tmpDir . '/probe_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath)) . '.json';
        $probeData = null;
        if (file_exists($probeCache) && filesize($probeCache) > 0) {
            $probeData = @json_decode(@file_get_contents($probeCache), true);
        }
        if (!is_array($probeData) || empty($probeData['success'])) {
            $out = @shell_exec('timeout 4 python /shares/webplayer/stream_sub.py probe ' . safeShellArg($fullVideoPath) . ' 2>/dev/null');
            if (!empty($out)) {
                $parsed = @json_decode($out, true);
                if (is_array($parsed) && !empty($parsed['success'])) {
                    @file_put_contents($probeCache, $out);
                    $probeData = $parsed;
                }
            }
        }
        if (is_array($probeData) && !empty($probeData['subtitles'])) {
            foreach ($probeData['subtitles'] as $es) {
                $label = !empty($es['label']) ? str_replace(array('"', "\\", "\r", "\n"), '', $es['label']) : ('내장 자막 #' . intval($es['stream_id']));
                $lang2 = normalizeIsoLang2(isset($es['lang']) ? $es['lang'] : 'und', $label);
                $tracks[] = array(
                    'type' => 'emb',
                    'name' => $label,
                    'lang' => $lang2,
                    'stream' => intval($es['stream_id']),
                    'codec' => !empty($es['codec']) ? strtoupper($es['codec']) : 'SRT',
                    'is_kor' => ($lang2 === 'ko') ? 0 : 1,
                    'is_forced' => !empty($es['is_forced']) ? 1 : 0,
                    'orig_idx' => count($tracks)
                );
            }
        }
    }

    // Prioritize Korean non-forced external > Korean non-forced embedded > Korean forced > other external > other embedded
    // Explicit orig_idx tie-breaker prevents PHP 5.6 unstable usort from shuffling Forced ahead of Normal!
    usort($tracks, function($a, $b) {
        if ($a['is_kor'] !== $b['is_kor']) return $a['is_kor'] - $b['is_kor'];
        if ($a['is_forced'] !== $b['is_forced']) return $a['is_forced'] - $b['is_forced'];
        $aExt = ($a['type'] === 'ext') ? 0 : 1;
        $bExt = ($b['type'] === 'ext') ? 0 : 1;
        if ($aExt !== $bExt) return $aExt - $bExt;
        return $a['orig_idx'] - $b['orig_idx'];
    });

    // Ensure unique NAMEs in HLS Master Playlist (Apple AVPlayer requires unique NAME per GROUP-ID)
    $usedNames = array();
    foreach ($tracks as $i => &$tr) {
        $baseName = $tr['name'];
        $name = $baseName;
        $n = 2;
        while (isset($usedNames[$name])) {
            $name = $baseName . ' (' . $n . ')';
            $n++;
        }
        $usedNames[$name] = true;
        $tr['name'] = $name;
    }
    unset($tr);
    return $tracks;
}

// -------------------------------------------------------------
// Action 3a: Apple HLS Master Playlist (.m3u8) with Native WebVTT Subtitles
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_master') {
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

    $encodedVideo = rawurlencode($videoRel);
    $fsize = (float)getSafeFileSize($fullVideoPath);
    $subTracks = collectHlsSubtitleTracks($fullVideoPath, $videoRel, $baseDir);

    // Fast path: Pure-PHP HLS v7 fMP4
    $fmp4Idx = function_exists('fmp4GetIndex') ? fmp4GetIndex($fullVideoPath) : false;
    if ($fmp4Idx !== false) {
        $dur = max(1.0, (float)$fmp4Idx['duration']);
        $bw = ($fsize > 0) ? (int)max(1000000, min(20000000, ($fsize * 8.0) / $dur)) : 8000000;
        $codecs = $fmp4Idx['v']['rfc'];
        if (!empty($fmp4Idx['a']['rfc'])) $codecs .= ',' . $fmp4Idx['a']['rfc'];
        $resAttr = ',RESOLUTION=' . intval($fmp4Idx['v']['w']) . 'x' . intval($fmp4Idx['v']['h']);

        $subLines = '';
        $subGroupAttr = '';
        if (!empty($subTracks)) {
            $subGroupAttr = ',SUBTITLES="subs"';
            foreach ($subTracks as $ti => $tr) {
                $defStr = ($ti === 0) ? 'YES' : 'NO';
                if ($tr['type'] === 'ext') {
                    $subUri = 'api.php?action=hls_sub_m3u8&video=' . $encodedVideo . '&src=ext&sub=' . rawurlencode($tr['sub_rel']) . '&dur=' . sprintf('%.3f', $dur) . '&ts=0&ext=.m3u8';
                } else {
                    $subUri = 'api.php?action=hls_sub_m3u8&video=' . $encodedVideo . '&src=emb&stream=' . intval($tr['stream']) . '&codec=' . rawurlencode($tr['codec']) . '&dur=' . sprintf('%.3f', $dur) . '&ts=0&ext=.m3u8';
                }
                $subLines .= '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="' . $tr['name'] . '",DEFAULT=' . $defStr . ',AUTOSELECT=' . $defStr . ',FORCED=NO,LANGUAGE="' . $tr['lang'] . '",URI="' . $subUri . "\"\n";
            }
        }

        $body = "#EXTM3U\n"
            . "#EXT-X-VERSION:7\n"
            . "#EXT-X-INDEPENDENT-SEGMENTS\n"
            . $subLines
            . "#EXT-X-STREAM-INF:BANDWIDTH=" . $bw . ",CODECS=\"" . $codecs . "\"" . $resAttr . $subGroupAttr . "\n"
            . "api.php?action=hls_manifest&video=" . $encodedVideo . "&ext=.m3u8\n";
        serveMemoryResponse($body, 'application/vnd.apple.mpegurl', 'private, max-age=300', false);
    }

    // Fallback: avconv MPEG-TS HLS v3
    $info = getHlsInfo($fullVideoPath);
    if (empty($info['success']) || empty($info['segments'])) {
        header('HTTP/1.1 422 Unprocessable Entity');
        echo "HLS remuxing not supported for this file";
        exit;
    }

    $dur = max(1.0, (float)$info['duration']);
    $bw = ($fsize > 0) ? (int)max(1000000, min(20000000, ($fsize * 8.0) / $dur)) : 8000000;
    $vCodecRfc = !empty($info['video_codec_rfc']) ? $info['video_codec_rfc'] : 'avc1.640028';
    $aCodec = isset($info['audio_codec']) ? strtolower($info['audio_codec']) : '';
    $aCodecRfc = !empty($info['audio_codec_rfc']) ? $info['audio_codec_rfc'] : '';
    $hasSupportedAudio = (isset($info['audio_stream']) && $info['audio_stream'] !== null && in_array($aCodec, array('aac', 'mp3', 'ac3', 'eac3')));
    if ($hasSupportedAudio && empty($aCodecRfc)) {
        $aCodecRfc = 'mp4a.40.2';
    }
    $codecs = $hasSupportedAudio ? ($vCodecRfc . ',' . $aCodecRfc) : $vCodecRfc;
    $resAttr = '';
    if (!empty($info['width']) && !empty($info['height'])) {
        $resAttr = ',RESOLUTION=' . intval($info['width']) . 'x' . intval($info['height']);
    }

    $subLines = '';
    $subGroupAttr = '';
    if (!empty($subTracks)) {
        $subGroupAttr = ',SUBTITLES="subs"';
        foreach ($subTracks as $ti => $tr) {
            $defStr = ($ti === 0) ? 'YES' : 'NO';
            if ($tr['type'] === 'ext') {
                $subUri = 'api.php?action=hls_sub_m3u8&video=' . $encodedVideo . '&src=ext&sub=' . rawurlencode($tr['sub_rel']) . '&dur=' . sprintf('%.3f', $dur) . '&ts=1&ext=.m3u8';
            } else {
                $subUri = 'api.php?action=hls_sub_m3u8&video=' . $encodedVideo . '&src=emb&stream=' . intval($tr['stream']) . '&codec=' . rawurlencode($tr['codec']) . '&dur=' . sprintf('%.3f', $dur) . '&ts=1&ext=.m3u8';
            }
            $subLines .= '#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="' . $tr['name'] . '",DEFAULT=' . $defStr . ',AUTOSELECT=YES,FORCED=NO,LANGUAGE="' . $tr['lang'] . '",URI="' . $subUri . "\"\n";
        }
    }

    $body = "#EXTM3U\n"
        . "#EXT-X-VERSION:3\n"
        . "#EXT-X-INDEPENDENT-SEGMENTS\n"
        . $subLines
        . "#EXT-X-STREAM-INF:BANDWIDTH=" . $bw . ",CODECS=\"" . $codecs . "\"" . $resAttr . $subGroupAttr . "\n"
        . "api.php?action=hls_manifest&video=" . $encodedVideo . "&ext=.m3u8\n";

    if (!isset($_SERVER['HTTP_RANGE'])) {
        spawnHlsPrefetch($fullVideoPath, 0);
    }
    serveMemoryResponse($body, 'application/vnd.apple.mpegurl', 'private, max-age=300', false);
}

// -------------------------------------------------------------
// Action 3e: HLS WebVTT Subtitle Media Playlist (.m3u8)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_sub_m3u8') {
    $src = isset($_GET['src']) ? $_GET['src'] : '';
    $dur = isset($_GET['dur']) ? max(1.0, (float)$_GET['dur']) : 3600.0;
    $tsFlag = (!empty($_GET['ts']) && $_GET['ts'] == '1') ? '1' : '0';
    $vttUrl = '';
    if ($src === 'ext') {
        $subRel = isset($_GET['sub']) ? trim($_GET['sub'], " /\\") : '';
        if (empty($subRel) || !validateRelativePath($subRel)) {
            header('HTTP/1.1 400 Bad Request');
            exit;
        }
        $vttUrl = 'api.php?action=hls_sub_vtt&hls=1&src=ext&sub=' . rawurlencode($subRel) . '&ts=' . $tsFlag . '&ext=.vtt';
    } elseif ($src === 'emb') {
        $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
        $stream = isset($_GET['stream']) ? intval($_GET['stream']) : -1;
        $codec = isset($_GET['codec']) ? preg_replace('/[^a-zA-Z0-9]/', '', $_GET['codec']) : 'SRT';
        if (empty($videoRel) || !validateRelativePath($videoRel) || $stream < 0) {
            header('HTTP/1.1 400 Bad Request');
            exit;
        }
        $vttUrl = 'api.php?action=hls_sub_vtt&hls=1&src=emb&video=' . rawurlencode($videoRel) . '&stream=' . $stream . '&codec=' . rawurlencode($codec) . '&ts=' . $tsFlag . '&ext=.vtt';
    } else {
        header('HTTP/1.1 400 Bad Request');
        exit;
    }
    $targetDur = (int)ceil($dur);
    $hlsVer = ($tsFlag === '1') ? '3' : '7';
    $body = "#EXTM3U\n"
        . "#EXT-X-VERSION:" . $hlsVer . "\n"
        . "#EXT-X-TARGETDURATION:" . $targetDur . "\n"
        . "#EXT-X-MEDIA-SEQUENCE:0\n"
        . "#EXT-X-PLAYLIST-TYPE:VOD\n"
        . "#EXT-X-INDEPENDENT-SEGMENTS\n"
        . sprintf("#EXTINF:%.3f,\n", $dur)
        . $vttUrl . "\n"
        . "#EXT-X-ENDLIST\n";
    serveMemoryResponse($body, 'application/vnd.apple.mpegurl', 'private, max-age=300', false);
}

function pruneVttRamCache($tmpDir) {
    $vttFiles = @glob($tmpDir . '/vtt*.vtt');
    if ($vttFiles && count($vttFiles) > 20) {
        usort($vttFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
        while (count($vttFiles) > 15) {
            @unlink(array_shift($vttFiles));
        }
    }
}

// -------------------------------------------------------------
// Action 3f: Native UTF-8 WebVTT Subtitle Converter & Endpoint (.vtt)
// Used by both HLS #EXT-X-MEDIA:TYPE=SUBTITLES and direct MP4 <track> on iOS!
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_sub_vtt') {
    $src = isset($_GET['src']) ? $_GET['src'] : '';
    $isHlsVtt = (!empty($_GET['hls']) && $_GET['hls'] == '1');
    // RFC 8216 §3.5: HLS WebVTT segments require X-TIMESTAMP-MAP (MPEGTS:0 for fMP4, 126000 for MPEG-TS 1.4s).
    // Plain HTML5 <track> (non-HLS) omits X-TIMESTAMP-MAP (-1).
    $mpegtsOffset = $isHlsVtt ? ((!empty($_GET['ts']) && $_GET['ts'] == '1') ? 126000 : 0) : -1;
    $syncOffset = isset($_GET['offset']) ? max(-60.0, min(60.0, (float)$_GET['offset'])) : 0.0;
    $tmpDir = '/tmp/webplayer_sub_ram';
    if (!is_dir($tmpDir)) @mkdir($tmpDir, 0777, true);

    if ($src === 'ext') {
        $subRel = isset($_GET['sub']) ? trim($_GET['sub'], " /\\") : '';
        if (empty($subRel) || !validateRelativePath($subRel)) {
            header('HTTP/1.1 400 Bad Request');
            exit;
        }
        $rawPath = $baseDir . '/' . $subRel;
        if (is_link($rawPath)) {
            header('HTTP/1.1 403 Forbidden');
            exit;
        }
        $fullSubPath = realpath($rawPath);
        if ($fullSubPath === false || !isWithinBaseDir($fullSubPath, $baseDir) || !is_file($fullSubPath)) {
            header('HTTP/1.1 404 Not Found');
            exit;
        }
        $ext = strtolower(pathinfo($fullSubPath, PATHINFO_EXTENSION));
        if (!in_array($ext, $subExts)) {
            header('HTTP/1.1 403 Forbidden');
            exit;
        }
        $vttCache = $tmpDir . '/vtt2_ext_' . md5($fullSubPath . ':' . @filemtime($fullSubPath) . ':' . $mpegtsOffset . ':' . sprintf('%.2f', $syncOffset)) . '.vtt';
        if (file_exists($vttCache) && filesize($vttCache) > 0) {
            $vtt = @file_get_contents($vttCache);
        } else {
            $rawSub = @file_get_contents($fullSubPath);
            $vtt = convertSubContentToVtt($rawSub !== false ? $rawSub : '', $ext, $mpegtsOffset, $syncOffset);
            @file_put_contents($vttCache, $vtt);
            pruneVttRamCache($tmpDir);
        }
        serveMemoryResponse($vtt, 'text/vtt; charset=utf-8', 'private, max-age=300', true);
    } elseif ($src === 'emb') {
        $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
        $stream = isset($_GET['stream']) ? intval($_GET['stream']) : -1;
        $codec = isset($_GET['codec']) ? strtolower(preg_replace('/[^a-zA-Z0-9]/', '', $_GET['codec'])) : 'srt';
        if (empty($videoRel) || !validateRelativePath($videoRel) || $stream < 0) {
            header('HTTP/1.1 400 Bad Request');
            exit;
        }
        $rawPath = $baseDir . '/' . $videoRel;
        if (is_link($rawPath)) {
            header('HTTP/1.1 403 Forbidden');
            exit;
        }
        $fullVideoPath = realpath($rawPath);
        if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !is_file($fullVideoPath)) {
            header('HTTP/1.1 404 Not Found');
            exit;
        }
        $vttCache = $tmpDir . '/vtt2_emb_' . md5($fullVideoPath . ':' . @filemtime($fullVideoPath) . ':' . $stream . ':' . $mpegtsOffset . ':' . sprintf('%.2f', $syncOffset)) . '.vtt';
        if (file_exists($vttCache) && filesize($vttCache) > 0) {
            $vtt = @file_get_contents($vttCache);
        } else {
            // Reuse stream_sub RAM cache if already extracted, otherwise extract cleanly
            $rawSubCache = $tmpDir . '/' . md5($fullVideoPath . ':' . $stream . ':' . @filemtime($fullVideoPath)) . '.' . $codec;
            if (file_exists($rawSubCache) && filesize($rawSubCache) > 0) {
                $rawSub = @file_get_contents($rawSubCache);
            } else {
                $cmd = 'export LANG=C.UTF-8 LC_ALL=C.UTF-8 LD_LIBRARY_PATH=/usr/local/wdmcserver/lib && timeout 15 python /shares/webplayer/stream_sub.py ' . safeShellArg($fullVideoPath) . ' ' . $stream . ' 2>/dev/null';
                $rawSub = @shell_exec($cmd);
                if (!empty($rawSub)) {
                    @file_put_contents($rawSubCache, $rawSub);
                }
            }
            $vtt = convertSubContentToVtt(!empty($rawSub) ? $rawSub : '', $codec, $mpegtsOffset, $syncOffset);
            @file_put_contents($vttCache, $vtt);
            pruneVttRamCache($tmpDir);
        }
        serveMemoryResponse($vtt, 'text/vtt; charset=utf-8', 'private, max-age=300', true);
    }
    header('HTTP/1.1 400 Bad Request');
    exit;
}

// -------------------------------------------------------------
// Action 3b: Direct Virtual HLS Media Playlist (.m3u8)
// Uses Pure-PHP HLS v7 fMP4 (~50ms/seg, zero avconv) when eligible,
// with seamless automatic fallback to avconv MPEG-TS HLS v3.
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

    $encodedVideo = rawurlencode($videoRel);

    // Fast path: Pure-PHP HLS v7 fMP4 (CMAF)
    $fmp4Idx = function_exists('fmp4GetIndex') ? fmp4GetIndex($fullVideoPath) : false;
    if ($fmp4Idx !== false && !empty($fmp4Idx['segments'])) {
        $maxDur = 2;
        foreach ($fmp4Idx['segments'] as $seg) {
            if ($seg['dur'] > $maxDur) {
                $maxDur = (int)ceil($seg['dur']);
            }
        }
        $lines = array(
            '#EXTM3U',
            '#EXT-X-VERSION:7',
            '#EXT-X-TARGETDURATION:' . $maxDur,
            '#EXT-X-MEDIA-SEQUENCE:0',
            '#EXT-X-PLAYLIST-TYPE:VOD',
            '#EXT-X-INDEPENDENT-SEGMENTS',
            '#EXT-X-MAP:URI="api.php?action=hls_init&video=' . $encodedVideo . '&ext=.mp4"'
        );
        foreach ($fmp4Idx['segments'] as $idx => $seg) {
            $lines[] = sprintf('#EXTINF:%.3f,', (float)$seg['dur']);
            $lines[] = 'api.php?action=hls_m4s&video=' . $encodedVideo . '&i=' . $idx . '&ext=.m4s';
        }
        $lines[] = '#EXT-X-ENDLIST';
        $body = implode("\n", $lines) . "\n";
        serveMemoryResponse($body, 'application/vnd.apple.mpegurl', 'private, max-age=300', true);
    }

    // Fallback: avconv MPEG-TS HLS v3
    $info = getHlsInfo($fullVideoPath);
    if (empty($info['success']) || empty($info['segments'])) {
        header('HTTP/1.1 422 Unprocessable Entity');
        echo "HLS remuxing not supported for this file";
        exit;
    }

    $maxDur = 4;
    foreach ($info['segments'] as $seg) {
        if ($seg['dur'] > $maxDur) {
            $maxDur = (int)ceil($seg['dur']);
        }
    }

    $lines = array(
        '#EXTM3U',
        '#EXT-X-VERSION:3',
        '#EXT-X-TARGETDURATION:' . $maxDur,
        '#EXT-X-MEDIA-SEQUENCE:0',
        '#EXT-X-PLAYLIST-TYPE:VOD',
        '#EXT-X-INDEPENDENT-SEGMENTS'
    );
    foreach ($info['segments'] as $idx => $seg) {
        $lines[] = sprintf('#EXTINF:%.3f,', (float)$seg['dur']);
        $lines[] = 'api.php?action=hls_seg&video=' . $encodedVideo . '&i=' . $idx . '&ext=.ts';
    }
    $lines[] = '#EXT-X-ENDLIST';
    $body = implode("\n", $lines) . "\n";

    // Pre-warm segment 0 in background while client parses the playlist
    if (!isset($_SERVER['HTTP_RANGE'])) {
        spawnHlsPrefetch($fullVideoPath, 0);
    }
    serveMemoryResponse($body, 'application/vnd.apple.mpegurl', 'private, max-age=300', true);
}

// -------------------------------------------------------------
// Action 3c: Pure-PHP fMP4 Initialization Segment (init.mp4)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_init') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    if (empty($videoRel) || !validateRelativePath($videoRel) || !function_exists('fmp4GetIndex')) {
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
    $fmp4Idx = fmp4GetIndex($fullVideoPath);
    if ($fmp4Idx === false) {
        header('HTTP/1.1 422 Unprocessable Entity');
        echo "fMP4 unavailable";
        exit;
    }
    $initBin = fmp4BuildInitSegment($fmp4Idx);
    serveMemoryResponse($initBin, 'video/mp4', 'private, max-age=3600', false);
}

// -------------------------------------------------------------
// Action 3d: Pure-PHP Zero-Copy fMP4 Media Segment (.m4s)
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'hls_m4s') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    $segIdx = isset($_GET['i']) ? intval($_GET['i']) : -1;
    if (empty($videoRel) || !validateRelativePath($videoRel) || $segIdx < 0 || !function_exists('fmp4GetIndex')) {
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
    $fmp4Idx = fmp4GetIndex($fullVideoPath);
    if ($fmp4Idx === false) {
        header('HTTP/1.1 422 Unprocessable Entity');
        echo "fMP4 unavailable";
        exit;
    }
    fmp4ServeSegment($fullVideoPath, $fmp4Idx, $segIdx);
}

// -------------------------------------------------------------
// Action 4: Zero-Disk On-Demand Continuous MPEG-TS Segment Remuxer
// (In-Process PHP TS Shift + Lookahead Prefetch + Byte-Range 206 for iOS Safari)
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

    $segCacheFile = buildHlsSegment($fullVideoPath, $info, $segIdx);
    if ($segCacheFile === false) {
        header('HTTP/1.1 500 Internal Server Error');
        echo "Remux failed";
        exit;
    }

    $segSize = @filesize($segCacheFile);
    if ($segSize === false || $segSize <= 0) {
        header('HTTP/1.1 500 Internal Server Error');
        echo "Empty segment";
        exit;
    }

    // Kick off non-blocking background prefetch of seg N+1 while seg N streams over the network
    if (!isset($_SERVER['HTTP_RANGE']) && ($segIdx + 1) < count($info['segments'])) {
        spawnHlsPrefetch($fullVideoPath, $segIdx + 1);
    }

    if (function_exists('apache_setenv')) @apache_setenv('no-gzip', '1');
    @ini_set('zlib.output_compression', '0');
    while (ob_get_level()) @ob_end_clean();

    header('Content-Type: video/mp2t');
    header('Accept-Ranges: bytes');
    header('Cache-Control: private, max-age=300');

    $start = 0;
    $end = $segSize - 1;
    if (isset($_SERVER['HTTP_RANGE']) && preg_match('/^bytes=\s*(\d*)-(\d*)$/i', trim($_SERVER['HTTP_RANGE']), $rm)) {
        if ($rm[1] !== '' && $rm[2] !== '') {
            $start = (int)$rm[1];
            $end = min($segSize - 1, (int)$rm[2]);
        } elseif ($rm[1] !== '') {
            $start = (int)$rm[1];
        } elseif ($rm[2] !== '') {
            $start = max(0, $segSize - (int)$rm[2]);
        }
        if ($start > $end || $start >= $segSize) {
            header('HTTP/1.1 416 Requested Range Not Satisfiable');
            header('Content-Range: bytes */' . $segSize);
            exit;
        }
        header('HTTP/1.1 206 Partial Content');
        header('Content-Range: bytes ' . $start . '-' . $end . '/' . $segSize);
        header('Content-Length: ' . ($end - $start + 1));
    } else {
        header('Content-Length: ' . $segSize);
    }

    $fp = @fopen($segCacheFile, 'rb');
    if ($fp) {
        if ($start > 0) fseek($fp, $start);
        $remaining = $end - $start + 1;
        while (!feof($fp) && $remaining > 0) {
            if (connection_aborted()) break;
            $chunk = fread($fp, min($remaining, 65536));
            if ($chunk === false || $chunk === '') break;
            echo $chunk;
            flush();
            $remaining -= strlen($chunk);
        }
        fclose($fp);
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
