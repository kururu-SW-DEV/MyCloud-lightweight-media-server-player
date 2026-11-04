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
function isWithinBaseDir($resolved, $base) {
    return $resolved === $base || strpos($resolved, $base . '/') === 0;
}

// WD My Cloud /shares/Public is a symlink to /DataVolume/shares/Public
$baseDir = realpath('/shares/Public');
if ($baseDir === false) {
    $baseDir = '/shares/Public';
}

$videoExts = array('mp4', 'mkv', 'webm', 'mov', 'avi', 'm4v', 'flv');
$subExts = array('smi', 'sami', 'srt', 'ass', 'ssa', 'vtt');
$ignoreList = array('.', '..', 'webplayer', 'incomplete', 'lost+found', '.DS_Store', 'Thumbs.db', 'desktop.ini', '.thumb');

// Helper: Make Apache Web URL from relative path
function makeWebUrl($relPath) {
    $parts = explode('/', trim(str_replace('\\', '/', $relPath), '/'));
    $encoded = array_map('rawurlencode', $parts);
    return '/media/' . implode('/', $encoded);
}

// Helper: Format bytes - pure integer branch without log() / pow() (Item 9)
function formatBytes($bytes, $precision = 2) {
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
    if (empty($videoRel)) {
        echo json_encode(array('success' => false, 'error' => 'No video specified'));
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath)) {
        echo json_encode(array('success' => false, 'error' => 'File not found'));
        exit;
    }
    
    // 1. High-speed zero-disk pure Python MKV probe (< 0.05s vs 2.5s avconv)
    $fastCmd = 'python /shares/webplayer/stream_sub.py probe ' . safeShellArg($fullVideoPath) . ' 2>/dev/null';
    $fastOut = @shell_exec($fastCmd);
    if (!empty($fastOut)) {
        $fastJson = @json_decode($fastOut, true);
        if ($fastJson && isset($fastJson['success']) && $fastJson['success'] && !empty($fastJson['subtitles'])) {
            echo $fastOut;
            exit;
        }
    }

    // 2. Fallback to avconv probe for non-MKV or unusual streams
    $cmd = 'export LANG=C.UTF-8 && export LC_ALL=C.UTF-8 && export LD_LIBRARY_PATH=/usr/local/wdmcserver/lib && /usr/local/wdmcserver/bin/avconv -probesize 65536 -analyzeduration 1000000 -i ' . safeShellArg($fullVideoPath) . ' 2>&1';
    $output = @shell_exec($cmd);
    
    $subs = array();
    $lines = explode("\n", $output);
    foreach ($lines as $line) {
        if (preg_match('/Stream #0[.:](\d+)(?:\(([^)]+)\))?: Subtitle: ([^,\n\r]+)/i', $line, $m)) {
            $s_id = $m[1];
            $lang = strtolower(trim($m[2]));
            if (empty($lang)) $lang = 'und';
            $codec = strtolower(trim($m[3]));
            
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
    
    echo json_encode(array('success' => true, 'subtitles' => $subs), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// -------------------------------------------------------------
// Action 2: On-demand Zero-Disk Stream Subtitle directly to client
// -------------------------------------------------------------
if (isset($_GET['action']) && $_GET['action'] === 'stream_sub') {
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\") : '';
    $streamId = isset($_GET['stream']) ? intval($_GET['stream']) : 0;
    $codec = isset($_GET['codec']) ? strtolower(trim($_GET['codec'])) : 'srt';
    // Whitelist only - $codec is concatenated straight into a cache file path
    // below, so anything else (e.g. "../../../shares/Public/evil") would let
    // a request write a file outside $tmpDir.
    if (!in_array($codec, array('srt', 'vtt', 'ass', 'ssa'), true)) {
        $codec = 'srt';
    }

    if (empty($videoRel)) {
        header('HTTP/1.1 400 Bad Request');
        echo "No video specified";
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || !isWithinBaseDir($fullVideoPath, $baseDir) || !file_exists($fullVideoPath)) {
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
    $procEnv = array('LANG' => 'C.UTF-8', 'LC_ALL' => 'C.UTF-8');
    $proc = @proc_open($cmd, $descriptors, $pipes, null, $procEnv);
    $cacheFp = @fopen($cacheFile . '.tmp', 'wb');
    
    if (is_resource($proc)) {
        fclose($pipes[0]);
        stream_set_blocking($pipes[1], 1);
        
        while (!feof($pipes[1])) {
            if (connection_aborted()) {
                @proc_terminate($proc, 9);
                break;
            }
            $buffer = fread($pipes[1], 8192);
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
        
        @proc_close($proc);
        if ($cacheFp) {
            fclose($cacheFp);
            @rename($cacheFile . '.tmp', $cacheFile);
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
    $ramFiles = @glob($tmpDir . '/*');
    if ($ramFiles && count($ramFiles) > 15) {
        usort($ramFiles, function($a, $b) { return filemtime($a) - filemtime($b); });
        while (count($ramFiles) > 10) {
            $old = array_shift($ramFiles);
            @unlink($old);
        }
    }
    exit;
}

header('Content-Type: application/json; charset=utf-8');
$mode = isset($_GET['all']) && $_GET['all'] == '1' ? 'all' : 'folder';

if ($mode === 'all') {
    $allVideos = array();
    $allSubs = array();
    
    $scanRecursive = function($dir, $depth = 0) use (&$scanRecursive, &$allVideos, &$allSubs, $baseDir, $videoExts, $subExts, $ignoreList) {
        if ($depth > 8 || count($allVideos) >= 2500) return;
        $items = @scandir($dir);
        if ($items === false) return;
        
        foreach ($items as $item) {
            if (in_array($item, $ignoreList) || $item[0] === '.') continue;
            $fullPath = $dir . '/' . $item;
            
            if (is_dir($fullPath)) {
                $scanRecursive($fullPath, $depth + 1);
            } else if (is_file($fullPath)) {
                $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
                $relPath = ltrim(substr($fullPath, strlen($baseDir)), '/\\');
                $folderRel = ltrim(substr($dir, strlen($baseDir)), '/\\');
                $baseName = pathinfo($item, PATHINFO_FILENAME);
                
                if (in_array($ext, $videoExts)) {
                    $size = @filesize($fullPath);
                    if ($size <= 0) continue;
                    $mtime = @filemtime($fullPath);
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
                } else if (in_array($ext, $subExts)) {
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
        foreach ($subsByFolder[$video['folder']] as $sub) {
            $subBase = $sub['basename'];
            if ($subBase === $vidBase || strpos($subBase, $vidBase) === 0) {
                $video['subtitles'][] = $sub;
            }
        }
    }
    unset($video);
    
    usort($allVideos, function($a, $b) {
        return strnatcasecmp($a['name'], $b['name']);
    });
    
    $etag = '"' . md5($baseDir . ':' . @filemtime($baseDir) . ':' . count($allVideos)) . '"';
    header('ETag: ' . $etag);
    if (isset($_SERVER['HTTP_IF_NONE_MATCH']) && trim($_SERVER['HTTP_IF_NONE_MATCH']) === $etag) {
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
    $resolved = realpath($baseDir . '/' . $requestDir);
    if ($resolved !== false && isWithinBaseDir($resolved, $baseDir) && is_dir($resolved)) {
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
$allFiles = array();
$rawDirs = array();

foreach ($items as $item) {
    if (in_array($item, $ignoreList) || $item[0] === '.') continue;
    $fullPath = $targetDir . '/' . $item;
    
    if (is_dir($fullPath)) {
        $rawDirs[] = $item;
    } else if (is_file($fullPath)) {
        $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
        $allFiles[] = $item;
        if (in_array($ext, $subExts)) {
            $baseName = pathinfo($item, PATHINFO_FILENAME);
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
foreach ($allFiles as $item) {
    $ext = strtolower(pathinfo($item, PATHINFO_EXTENSION));
    if (!in_array($ext, $videoExts)) continue;
    
    $baseName = pathinfo($item, PATHINFO_FILENAME);
    $fullPath = $targetDir . '/' . $item;
    $size = @filesize($fullPath);
    if ($size <= 0) continue;
    $mtime = @filemtime($fullPath);
    
    $matchedSubs = array();
    foreach ($subtitlesMap as $subItem => $subInfo) {
        $subBase = $subInfo['basename'];
        if ($subBase === $baseName || strpos($subBase, $baseName) === 0) {
            $matchedSubs[] = $subInfo;
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

$etag = '"' . md5($targetDir . ':' . @filemtime($targetDir) . ':' . count($items)) . '"';
header('ETag: ' . $etag);
if (isset($_SERVER['HTTP_IF_NONE_MATCH']) && trim($_SERVER['HTTP_IF_NONE_MATCH']) === $etag) {
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
