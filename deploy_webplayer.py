import os
import sys
import re
import time
from ssh_client import get_ssh_client

APACHE_CONF = """Alias /player /shares/Public/webplayer
<Directory /shares/Public/webplayer>
    Options Indexes FollowSymLinks
    AllowOverride All
    Require all granted
    DirectoryIndex index.html index.php
</Directory>

Alias /media /shares/Public
<Directory /shares/Public>
    Options Indexes FollowSymLinks
    AllowOverride None
    Require all granted

    <IfModule mod_headers.c>
        Header set Accept-Ranges bytes
        Header set Access-Control-Allow-Origin "*"
    </IfModule>

    AddType video/mp4 .mp4
    AddType video/webm .webm
    AddType video/x-matroska .mkv
    AddType video/ogg .ogv

    AddType text/vtt .vtt
    AddType text/plain;charset=utf-8 .smi .sami .srt .ass .ssa
</Directory>
"""

STREAM_SUB_PY = r'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
stream_sub.py - Zero-disk high-speed on-demand MKV subtitle engine for WD My Cloud Gen 1
Provides:
  1. Ultra-fast MKV subtitle track probing (< 10ms vs 2500ms avconv)
  2. Sub-second direct-seek Cues streaming (< 0.1s to first subtitle dialogue)
  3. Automatic fallback to sequential stream for non-indexed MKV tracks
"""
import os
import sys
import json
import struct
import subprocess
import signal

try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass

def read_vint(data, pos):
    if pos >= len(data): return None, 0
    b0 = ord(data[pos])
    for length in range(1, 9):
        if b0 & (0x80 >> (length - 1)):
            mask = (1 << (8 - length)) - 1
            val = b0 & mask
            for i in range(1, length):
                if pos + i >= len(data): return None, 0
                val = (val << 8) | ord(data[pos + i])
            return val, length
    return None, 0

def read_id(data, pos):
    if pos >= len(data): return None, 0
    b0 = ord(data[pos])
    for length in range(1, 5):
        if b0 & (0x80 >> (length - 1)):
            val = b0
            for i in range(1, length):
                if pos + i >= len(data): return None, 0
                val = (val << 8) | ord(data[pos + i])
            return val, length
    return None, 0

def ms_to_srt(ms):
    if ms < 0: ms = 0
    h = ms // 3600000
    m = (ms % 3600000) // 60000
    s = (ms % 60000) // 1000
    millis = ms % 1000
    return "%02d:%02d:%02d,%03d" % (h, m, s, millis)

def get_language_label(lang):
    lang = lang.lower().strip()
    if lang in ('kor', 'ko', 'korean'): return u'한국어'
    if lang in ('eng', 'en', 'english'): return u'영어'
    if lang in ('jpn', 'ja', 'japanese'): return u'일본어'
    if lang in ('chi', 'zh', 'chinese'): return u'중국어'
    if lang in ('fre', 'fra', 'fr'): return u'프랑스어'
    if lang in ('ger', 'deu', 'de'): return u'독일어'
    if lang in ('spa', 'es'): return u'스페인어'
    if lang in ('rus', 'ru'): return u'러시아어'
    if lang in ('ita', 'it'): return u'이탈리아어'
    if lang in ('pol', 'pl'): return u'폴란드어'
    if lang in ('por', 'pt'): return u'포르투갈어'
    if lang in ('tha', 'th'): return u'태국어'
    if lang in ('vie', 'vi'): return u'베트남어'
    if lang in ('ara', 'ar'): return u'아랍어'
    if lang in ('hin', 'hi'): return u'힌디어'
    if lang in ('ind', 'id'): return u'인도네시아어'
    if not lang or lang == 'und': return u'기타'
    return lang.upper()

def parse_mkv_seekhead(f):
    f.seek(0)
    hdr = f.read(65536)
    seg_idx = hdr.find(b'\x18\x53\x80\x67')
    if seg_idx == -1: return None, None, None
    
    b0 = ord(hdr[seg_idx + 4])
    sl = 1
    for length in range(1, 9):
        if b0 & (0x80 >> (length - 1)):
            sl = length
            break
    seg_data_start = seg_idx + 4 + sl
    
    sh_idx = hdr.find(b'\x11\x4d\x9b\x74')
    if sh_idx == -1: return seg_data_start, None, None
    
    sh_sz, sh_len = read_vint(hdr, sh_idx + 4)
    if sh_sz is None: return seg_data_start, None, None
    sh_end = sh_idx + 4 + sh_len + sh_sz
    sh_data = hdr[sh_idx + 4 + sh_len : sh_end]
    
    tracks_offset = None
    cues_offset = None
    
    p = 0
    while p < len(sh_data) - 4:
        if ord(sh_data[p]) == 0x4D and ord(sh_data[p+1]) == 0xBB:
            sp = p + 2
            ssz, sl = read_vint(sh_data, sp)
            sp += sl
            send = sp + ssz
            sid = None
            spos = None
            while sp < send:
                tag = ord(sh_data[sp])
                if tag == 0x53 and ord(sh_data[sp+1]) == 0xAB:
                    tsz = ord(sh_data[sp+2]) & 0x7F
                    sid = sh_data[sp+3:sp+3+tsz]
                    sp += 3 + tsz
                elif tag == 0x53 and ord(sh_data[sp+1]) == 0xAC:
                    tsz = ord(sh_data[sp+2]) & 0x7F
                    pval = 0
                    for i in range(tsz): pval = (pval << 8) | ord(sh_data[sp+3+i])
                    spos = pval
                    sp += 3 + tsz
                else:
                    sp += 1
            if sid == b'\x16\x54\xae\x6b':
                tracks_offset = spos
            elif sid == b'\x1c\x53\xbb\x6b':
                cues_offset = spos
        p += 1
        
    return seg_data_start, tracks_offset, cues_offset

def probe_subtitles(video_path):
    try:
        f = open(video_path, 'rb')
    except Exception as e:
        print json.dumps({'success': False, 'error': str(e)})
        return
        
    seg_data_start, tracks_offset, cues_offset = parse_mkv_seekhead(f)
    if seg_data_start is None or tracks_offset is None:
        f.close()
        # Fallback to avconv probe
        return fallback_avconv_probe(video_path)
        
    f.seek(seg_data_start + tracks_offset)
    tid_b = f.read(12)
    tid, tl = read_id(tid_b, 0)
    tsz, tsl = read_vint(tid_b, tl)
    f.seek(seg_data_start + tracks_offset + tl + tsl)
    tracks_data = f.read(tsz)
    f.close()
    
    p = 0
    cur_stream = 0
    subs = []
    
    while p < len(tracks_data):
        eid, el = read_id(tracks_data, p)
        if eid is None: break
        esz, esl = read_vint(tracks_data, p + el)
        if esz is None: break
        entry_end = p + el + esl + esz
        
        if eid == 0xAE: # TrackEntry
            ep = p + el + esl
            tnum = None
            ttype = None
            tcodec = None
            tlang = 'und'
            tname = ''
            tdef = 1
            tforced = 0
            
            while ep < entry_end:
                ieid, iel = read_id(tracks_data, ep)
                if ieid is None: break
                isz, isl = read_vint(tracks_data, ep + iel)
                if isz is None: break
                vpos = ep + iel + isl
                
                if ieid == 0xD7: # TrackNumber
                    v = 0
                    for i in range(isz): v = (v << 8) | ord(tracks_data[vpos + i])
                    tnum = v
                elif ieid == 0x83: # TrackType
                    ttype = ord(tracks_data[vpos])
                elif ieid == 0x86: # CodecID
                    tcodec = tracks_data[vpos : vpos + isz]
                elif ieid == 0x22B59C: # Language
                    tlang = tracks_data[vpos : vpos + isz]
                elif ieid == 0x536E: # Name
                    tname = tracks_data[vpos : vpos + isz]
                elif ieid == 0x88: # FlagDefault
                    tdef = ord(tracks_data[vpos])
                elif ieid == 0x55AA: # FlagForced
                    tforced = ord(tracks_data[vpos])
                ep = vpos + isz
                
            if ttype == 17: # Subtitle
                codec_label = 'SRT'
                if tcodec and ('ASS' in tcodec or 'SSA' in tcodec):
                    codec_label = 'ASS'
                lang_label = get_language_label(tlang)
                label = u"[내장-%s] %s 자막 (%s)" % (lang_label, lang_label, codec_label)
                if tforced: label += u" [강제/일부]"
                elif tdef: label += u" [기본]"
                if tname:
                    try:
                        uname = tname.decode('utf-8', errors='replace')
                        label += u" - " + uname
                    except: pass
                    
                subs.append({
                    'stream_id': cur_stream,
                    'track_number': tnum,
                    'lang': tlang,
                    'lang_label': lang_label,
                    'label': label,
                    'codec': codec_label,
                    'is_default': bool(tdef),
                    'is_forced': bool(tforced),
                    'embedded': True
                })
            cur_stream += 1
        p = entry_end
        
    # Sort: Korean first, then English, then others; non-forced first
    def sub_sort_key(s):
        lang = s['lang'].lower()
        is_kor = 0 if (lang in ('kor', 'ko', 'korean')) else 1
        is_forced = 1 if s['is_forced'] else 0
        return (is_kor, is_forced, s['stream_id'])
        
    subs.sort(key=sub_sort_key)
    print json.dumps({'success': True, 'subtitles': subs})

def fallback_avconv_probe(video_path):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/local/wdmcserver/lib'
    cmd = ['/usr/local/wdmcserver/bin/avconv', '-probesize', '32768', '-analyzeduration', '0', '-i', video_path]
    try:
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr_data = p.communicate()
    except Exception as e:
        print json.dumps({'success': False, 'error': str(e)})
        return
        
    subs = []
    for line in stderr_data.splitlines():
        if 'Subtitle:' in line:
            import re
            m = re.search(r'Stream #0[.:](\d+)(?:\(([^)]+)\))?: Subtitle: ([^,\n\r]+)', line)
            if m:
                s_id = int(m.group(1))
                lang = (m.group(2) or 'und').strip().lower()
                codec = m.group(3).strip()
                lang_label = get_language_label(lang)
                is_def = '(default)' in line
                is_forced = '(forced)' in line
                codec_label = 'ASS' if ('ass' in codec.lower() or 'ssa' in codec.lower()) else 'SRT'
                label = u"[내장-%s] %s 자막 (%s)" % (lang_label, lang_label, codec_label)
                if is_forced: label += u" [강제/일부]"
                elif is_def: label += u" [기본]"
                subs.append({
                    'stream_id': s_id,
                    'lang': lang,
                    'lang_label': lang_label,
                    'label': label,
                    'codec': codec_label,
                    'is_default': is_def,
                    'is_forced': is_forced,
                    'embedded': True
                })
    print json.dumps({'success': True, 'subtitles': subs})

def stream_subtitles_cues(video_path, stream_id):
    try:
        f = open(video_path, 'rb')
    except Exception as e:
        sys.stderr.write("Failed to open file: %s\n" % e)
        fallback_avconv_stream(video_path, stream_id)
        return
        
    target_stream_idx = int(stream_id)
    seg_data_start, tracks_offset, cues_offset = parse_mkv_seekhead(f)
    if seg_data_start is None or tracks_offset is None or cues_offset is None:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    # Read tracks data
    f.seek(seg_data_start + tracks_offset)
    tid_b = f.read(12)
    tid, tl = read_id(tid_b, 0)
    tsz, tsl = read_vint(tid_b, tl)
    f.seek(seg_data_start + tracks_offset + tl + tsl)
    tracks_data = f.read(tsz)
    
    p = 0
    cur_stream = 0
    target_track_num = None
    target_codec = None
    codec_private = b''
    
    while p < len(tracks_data):
        eid, el = read_id(tracks_data, p)
        if eid is None: break
        esz, esl = read_vint(tracks_data, p + el)
        if esz is None: break
        entry_end = p + el + esl + esz
        if eid == 0xAE:
            ep = p + el + esl
            tnum = None
            ttype = None
            tcodec = None
            tpriv = b''
            while ep < entry_end:
                ieid, iel = read_id(tracks_data, ep)
                if ieid is None: break
                isz, isl = read_vint(tracks_data, ep + iel)
                if isz is None: break
                vpos = ep + iel + isl
                if ieid == 0xD7:
                    v = 0
                    for i in range(isz): v = (v << 8) | ord(tracks_data[vpos + i])
                    tnum = v
                elif ieid == 0x83:
                    ttype = ord(tracks_data[vpos])
                elif ieid == 0x86:
                    tcodec = tracks_data[vpos : vpos + isz]
                elif ieid == 0x63A2:
                    tpriv = tracks_data[vpos : vpos + isz]
                ep = vpos + isz
            is_sub = (ttype == 17) or (tcodec and 'S_' in tcodec)
            if is_sub and (cur_stream == target_stream_idx or tnum == target_stream_idx):
                target_track_num = tnum
                target_codec = tcodec
                codec_private = tpriv
                break
            cur_stream += 1
        p = entry_end
        
    if target_track_num is None:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    # Read Cues
    f.seek(seg_data_start + cues_offset)
    cid_b = f.read(12)
    cid, cl = read_id(cid_b, 0)
    csz, csl = read_vint(cid_b, cl)
    f.seek(seg_data_start + cues_offset + cl + csl)
    cues_data = f.read(csz)
    
    # Fast search for target track
    # In EBML, TrackNumber in CueTrack (0xF7) is a vint
    if target_track_num < 128:
        track_sig = b'\xf7\x81' + chr(target_track_num)
    else:
        track_sig = b'\xf7\x82' + chr(target_track_num >> 8) + chr(target_track_num & 0xFF)
        
    cues = []
    pos = 0
    while True:
        idx = cues_data.find(track_sig, pos)
        if idx == -1: break
        pos = idx + len(track_sig)
        
        b7_idx = cues_data.rfind(b'\xb7', max(0, idx - 10), idx)
        if b7_idx == -1: continue
        
        b0 = ord(cues_data[b7_idx+1])
        b7_len = 1
        for l in range(1, 9):
            if b0 & (0x80 >> (l - 1)):
                b7_len = l
                break
        b7_sz = b0 & ((1 << (8 - b7_len)) - 1)
        for i in range(1, b7_len): b7_sz = (b7_sz << 8) | ord(cues_data[b7_idx+1+i])
        
        _, el = read_id(cues_data, b7_idx)
        esz, esl = read_vint(cues_data, b7_idx + el)
        if esz is None: continue
        
        tp = b7_idx + el + esl
        tp_end = tp + esz
        cpos = None
        rpos = 0
        dur = 0
        
        while tp < tp_end:
            tag_id, id_len = read_id(cues_data, tp)
            if tag_id is None: break
            tag_sz, sz_len = read_vint(cues_data, tp + id_len)
            if tag_sz is None: break
            vpos = tp + id_len + sz_len
            if tag_id == 0xF1: # CueClusterPosition
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                cpos = v
            elif tag_id == 0xF0: # CueRelativePosition
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                rpos = v
            elif tag_id == 0xB2: # CueDuration
                v = 0
                for i in range(tag_sz): v = (v << 8) | ord(cues_data[vpos + i])
                dur = v
            tp = vpos + tag_sz
                
        if cpos is not None:
            t_idx = cues_data.rfind(b'\xb3', max(0, b7_idx - 30), b7_idx)
            ctime = 0
            if t_idx != -1:
                _, tl = read_id(cues_data, t_idx)
                tsz, tsl = read_vint(cues_data, t_idx + tl)
                if tsz is not None:
                    v = 0
                    for i in range(tsz): v = (v << 8) | ord(cues_data[t_idx + tl + tsl + i])
                    ctime = v
            cues.append((ctime, dur, cpos, rpos))
            
    if not cues:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return
        
    is_ass = bool(target_codec and ('ASS' in target_codec or 'SSA' in target_codec))
    if is_ass and codec_private:
        try:
            sys.stdout.write(codec_private)
            if not codec_private.endswith('\n'):
                sys.stdout.write('\n')
            sys.stdout.write("[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            sys.stdout.flush()
        except IOError:
            sys.exit(0)
            
    cue_idx = 1
    cluster_cache = {}
    for ctime, dur, cpos, rpos in cues:
        abs_cluster = seg_data_start + cpos
        if cpos in cluster_cache:
            cluster_data_start = cluster_cache[cpos]
        else:
            f.seek(abs_cluster + 4)
            b0 = ord(f.read(1))
            vlen = 1
            for l in range(1, 9):
                if b0 & (0x80 >> (l - 1)):
                    vlen = l
                    break
            cluster_data_start = abs_cluster + 4 + vlen
            cluster_cache[cpos] = cluster_data_start
            
        if rpos > 0:
            f.seek(cluster_data_start + rpos)
        else:
            f.seek(cluster_data_start)
            
        block_hdr = f.read(4096)
        txt = None
        b_dur = dur
        
        eid, el = read_id(block_hdr, 0)
        if eid == 0xA0: # BlockGroup
            esz, esl = read_vint(block_hdr, el)
            if esz is not None:
                bg_data = block_hdr[el + esl : el + esl + esz]
                bp = 0
                while bp < len(bg_data):
                    bid, bl = read_id(bg_data, bp)
                    if bid is None: break
                    bsz, bsl = read_vint(bg_data, bp + bl)
                    if bsz is None: break
                    if bid == 0xA1: # Block
                        block_payload = bg_data[bp + bl + bsl : bp + bl + bsl + bsz]
                        tnum, tlen = read_vint(block_payload, 0)
                        if tnum == target_track_num:
                            txt = block_payload[tlen + 3:]
                            break
                    elif bid == 0x9B: # BlockDuration
                        dv = 0
                        for i in range(bsz): dv = (dv << 8) | ord(bg_data[bp + bl + bsl + i])
                        b_dur = dv
                    bp += bl + bsl + bsz
        elif eid == 0xA1 or eid == 0xA3: # Block or SimpleBlock
            esz, esl = read_vint(block_hdr, el)
            if esz is not None:
                block_payload = block_hdr[el + esl : el + esl + esz]
                tnum, tlen = read_vint(block_payload, 0)
                if tnum == target_track_num:
                    txt = block_payload[tlen + 3:]
                    
        # Fallback linear scan inside block_hdr if not matched at offset
        if not txt:
            p = 0
            while p < len(block_hdr) - 4:
                tag = ord(block_hdr[p])
                if tag == 0xA0:
                    _, vlen = read_vint(block_hdr, p + 1)
                    p += 1 + (vlen if vlen else 1)
                elif tag == 0xA1 or tag == 0xA3:
                    bsz, bsl = read_vint(block_hdr, p + 1)
                    if bsz is None: break
                    block_payload = block_hdr[p + 1 + bsl : p + 1 + bsl + bsz]
                    tnum, tlen = read_vint(block_payload, 0)
                    if tnum == target_track_num:
                        txt = block_payload[tlen + 3:]
                        break
                    p += 1 + bsl + bsz
                elif tag == 0x9B:
                    dsz, dsl = read_vint(block_hdr, p + 1)
                    if dsz is None: break
                    dv = 0
                    for i in range(dsz): dv = (dv << 8) | ord(block_hdr[p + 1 + dsl + i])
                    b_dur = dv
                    p += 1 + dsl + dsz
                else:
                    p += 1
                    
        if txt:
            start_ms = ctime
            end_ms = ctime + (b_dur if b_dur > 0 else 3000)
            try:
                if is_ass:
                    parts = txt.split(',', 8)
                    if len(parts) >= 9:
                        layer = parts[1]
                        style = parts[2]
                        name = parts[3]
                        ml = parts[4]
                        mr = parts[5]
                        mv = parts[6]
                        effect = parts[7]
                        text = parts[8]
                        def ms_to_ass(ms):
                            h, rem = divmod(ms, 3600000)
                            m, rem = divmod(rem, 60000)
                            s, ms_part = divmod(rem, 1000)
                            cs = ms_part // 10
                            return "%d:%02d:%02d.%02d" % (h, m, s, cs)
                        line = "Dialogue: %s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" % (
                            layer, ms_to_ass(start_ms), ms_to_ass(end_ms), style, name, ml, mr, mv, effect, text.strip()
                        )
                        sys.stdout.write(line)
                    else:
                        out = "%d\n%s --> %s\n%s\n\n" % (cue_idx, ms_to_srt(start_ms), ms_to_srt(end_ms), txt.strip())
                        sys.stdout.write(out)
                else:
                    out = "%d\n%s --> %s\n%s\n\n" % (cue_idx, ms_to_srt(start_ms), ms_to_srt(end_ms), txt.strip())
                    sys.stdout.write(out)
                sys.stdout.flush()
                cue_idx += 1
            except IOError:
                break
                
    f.close()

def fallback_avconv_stream(video_path, stream_id):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/local/wdmcserver/lib'
    env['LANG'] = 'C.UTF-8'
    env['LC_ALL'] = 'C.UTF-8'
    cmd = [
        '/usr/local/wdmcserver/bin/avconv',
        '-y',
        '-threads', '2',
        '-vn', '-an',
        '-i', video_path,
        '-map', '0:' + str(stream_id),
        '-c:s', 'copy',
        '-f', 'matroska',
        '-'
    ]
    try:
        devnull = open('/dev/null', 'w')
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=devnull, bufsize=65536)
    except Exception:
        return
        
    buf = b''
    cluster_tag = b'\x1f\x43\xb6\x75'
    cue_idx = 1
    pending_cue = None

    def emit_cue(cue_tuple):
        try:
            idx, s_ms, e_ms, txt, _ = cue_tuple
            out = "%d\n%s --> %s\n%s\n\n" % (idx, ms_to_srt(s_ms), ms_to_srt(e_ms), txt)
            sys.stdout.write(out)
            sys.stdout.flush()
        except IOError:
            try: p.kill()
            except: pass
            sys.exit(0)

    while True:
        try:
            chunk = p.stdout.read(16384)
        except Exception:
            break
        if not chunk:
            if p.poll() is not None: break
            continue
        buf += chunk
        while True:
            c1 = buf.find(cluster_tag)
            if c1 == -1:
                buf = buf[-3:]
                break
            c_size, c_len = read_vint(buf, c1 + 4)
            if c_size is None: break
            cluster_end = c1 + 4 + c_len + c_size
            if len(buf) < cluster_end: break
            cluster_data = buf[c1 : cluster_end]
            buf = buf[cluster_end:]
            p_pos = 4 + c_len
            tc = 0
            while p_pos < len(cluster_data):
                tag = ord(cluster_data[p_pos])
                if tag == 0xE7:
                    s, l = read_vint(cluster_data, p_pos + 1)
                    p_pos += 1 + l
                    tc = 0
                    for i in range(s): tc = (tc << 8) | ord(cluster_data[p_pos + i])
                    p_pos += s
                elif tag == 0xA0 or tag == 0xA3:
                    tag_size, tag_len = read_vint(cluster_data, p_pos + 1)
                    inner_end = p_pos + 1 + tag_len + tag_size
                    bp = p_pos + 1 + tag_len
                    duration = 0
                    block_data = None
                    rel_tc = 0
                    if tag == 0xA0:
                        while bp < inner_end and bp < len(cluster_data):
                            btag = ord(cluster_data[bp])
                            if btag == 0xA1:
                                bs, bl = read_vint(cluster_data, bp + 1)
                                doff = bp + 1 + bl
                                tnum, tlen = read_vint(cluster_data, doff)
                                rel_tc = struct.unpack('>h', cluster_data[doff + tlen : doff + tlen + 2])[0]
                                block_data = cluster_data[doff + tlen + 3 : doff + bs]
                                bp = doff + bs
                            elif btag == 0x9B:
                                ds, dl = read_vint(cluster_data, bp + 1)
                                doff = bp + 1 + dl
                                dur = 0
                                for i in range(ds): dur = (dur << 8) | ord(cluster_data[doff + i])
                                duration = dur
                                bp = doff + ds
                            else:
                                sub_s, sub_l = read_vint(cluster_data, bp + 1)
                                if sub_s is None: break
                                bp = bp + 1 + sub_l + sub_s
                    else:
                        doff = bp
                        tnum, tlen = read_vint(cluster_data, doff)
                        rel_tc = struct.unpack('>h', cluster_data[doff + tlen : doff + tlen + 2])[0]
                        block_data = cluster_data[doff + tlen + 3 : doff + tag_size]
                    if block_data:
                        start_ms = tc + rel_tc
                        is_fallback = (duration <= 0)
                        end_ms = start_ms + (duration if duration > 0 else 4000)
                        txt = block_data.strip().replace('\r\n', '\n').replace('\r', '\n')
                        if pending_cue is not None:
                            p_idx, p_start, p_end, p_txt, p_is_fallback = pending_cue
                            if p_is_fallback and p_end > start_ms:
                                p_end = max(p_start + 500, start_ms)
                            emit_cue((p_idx, p_start, p_end, p_txt, p_is_fallback))
                        pending_cue = (cue_idx, start_ms, end_ms, txt, is_fallback)
                        cue_idx += 1
                    p_pos = inner_end
                else:
                    p_pos += 1
    if pending_cue is not None:
        emit_cue(pending_cue)
    try:
        p.stdout.close()
        devnull.close()
    except Exception:
        pass

if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: stream_sub.py probe <video_path> OR stream_sub.py <video_path> <stream_id>\n")
        sys.exit(1)
    if sys.argv[1] == 'probe':
        if len(sys.argv) < 3:
            sys.exit(1)
        probe_subtitles(sys.argv[2])
    else:
        if len(sys.argv) < 3:
            sys.exit(1)
        stream_subtitles_cues(sys.argv[1], sys.argv[2])
'''

API_PHP = """<?php
header('Access-Control-Allow-Origin: *');
@setlocale(LC_ALL, 'C.UTF-8');

function safeShellArg($arg) {
    return "'" . str_replace("'", "'\\\\''", $arg) . "'";
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
    $parts = explode('/', trim(str_replace('\\\\', '/', $relPath), '/'));
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
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\\\") : '';
    if (empty($videoRel)) {
        echo json_encode(array('success' => false, 'error' => 'No video specified'));
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || strpos($fullVideoPath, $baseDir) !== 0 || !file_exists($fullVideoPath)) {
        echo json_encode(array('success' => false, 'error' => 'File not found'));
        exit;
    }
    
    // 1. High-speed zero-disk pure Python MKV probe (< 0.05s vs 2.5s avconv)
    $fastCmd = 'python /shares/Public/webplayer/stream_sub.py probe ' . safeShellArg($fullVideoPath) . ' 2>/dev/null';
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
    $lines = explode("\\n", $output);
    foreach ($lines as $line) {
        if (preg_match('/Stream #0[.:](\\d+)(?:\\(([^)]+)\\))?: Subtitle: ([^,\\n\\r]+)/i', $line, $m)) {
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
    $videoRel = isset($_GET['video']) ? trim($_GET['video'], " /\\\\") : '';
    $streamId = isset($_GET['stream']) ? intval($_GET['stream']) : 0;
    $codec = isset($_GET['codec']) ? strtolower(trim($_GET['codec'])) : 'srt';
    
    if (empty($videoRel)) {
        header('HTTP/1.1 400 Bad Request');
        echo "No video specified";
        exit;
    }
    $fullVideoPath = realpath($baseDir . '/' . $videoRel);
    if ($fullVideoPath === false || strpos($fullVideoPath, $baseDir) !== 0 || !file_exists($fullVideoPath)) {
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
    $cmd = 'exec python /shares/Public/webplayer/stream_sub.py ' . safeShellArg($fullVideoPath) . ' ' . $streamId;
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
                $relPath = ltrim(substr($fullPath, strlen($baseDir)), '/\\\\');
                $folderRel = ltrim(substr($dir, strlen($baseDir)), '/\\\\');
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
    
    foreach ($allVideos as &$video) {
        foreach ($allSubs as $sub) {
            if ($sub['folder'] === $video['folder']) {
                $subBase = $sub['basename'];
                $vidBase = $video['basename'];
                if ($subBase === $vidBase || strpos($subBase, $vidBase) === 0) {
                    $video['subtitles'][] = $sub;
                }
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
$requestDir = isset($_GET['dir']) ? trim($_GET['dir'], " /\\\\") : '';
$targetDir = $baseDir;

if ($requestDir !== '') {
    $resolved = realpath($baseDir . '/' . $requestDir);
    if ($resolved !== false && strpos($resolved, $baseDir) === 0 && is_dir($resolved)) {
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
foreach ($rawDirs as $d) {
    $dRel = ($requestDir ? $requestDir . '/' : '') . $d;
    $dFull = $targetDir . '/' . $d;
    
    $vidCount = 0;
    $subDirCount = 0;
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
"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MyCloud Media Player</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="app-container">
        <!-- Header -->
        <header class="navbar">
            <div class="brand" onclick="switchMode('folder', '')" style="cursor: pointer;" title="홈으로 이동">
                <span class="icon">🎬</span>
                <h1>MyCloud <span>Media Player</span></h1>
            </div>
            <div class="search-bar">
                <input type="text" id="search-input" placeholder="영상 또는 폴더 검색..." autocomplete="off">
                <button id="clear-search" class="clear-btn" title="검색어 지우기">&times;</button>
            </div>
            <div class="nav-actions">
                <button id="refresh-btn" class="btn btn-secondary" title="새로고침">🔄 새로고침</button>
            </div>
        </header>

        <!-- Main Content -->
        <main class="main-content">
            <!-- Directory Path, Mode Toggle & Status -->
            <div class="breadcrumb-container">
                <div class="breadcrumbs" id="breadcrumbs">
                    <span class="crumb active" data-path="">🏠 Public</span>
                </div>
                <div class="toolbar-right">
                    <div class="view-mode-toggle">
                        <button id="mode-folder-btn" class="btn-mode active" title="폴더별 탐색">📁 폴더별</button>
                        <button id="mode-all-btn" class="btn-mode" title="모든 폴더의 영상을 한 번에 보기">🎬 전체 영상</button>
                    </div>
                    <div class="layout-toggle" title="목록 표시 형태">
                        <button id="layout-grid-btn" class="btn-layout" title="타일 형식으로 보기">🔲 타일</button>
                        <button id="layout-list-btn" class="btn-layout active" title="목록(리스트) 형식으로 보기">☰ 목록</button>
                    </div>
                    <div class="meta-toggle" title="파일 날짜 및 용량 표시 설정 (기본: 숨김)">
                        <button id="meta-hide-btn" class="btn-layout active" title="파일 날짜 및 용량 숨김 (기본값)">
                            <span class="toggle-text-full">🙈 날짜·용량 숨김</span>
                            <span class="toggle-text-short">🙈 숨김</span>
                        </button>
                        <button id="meta-show-btn" class="btn-layout" title="파일 날짜 및 용량 표시">
                            <span class="toggle-text-full">👁️ 날짜·용량 표시</span>
                            <span class="toggle-text-short">👁️ 표시</span>
                        </button>
                    </div>
                    <select id="sort-select" class="sort-select" title="정렬 기준">
                        <option value="name_asc" selected>🔤 이름순 (1,2,3..)</option>
                        <option value="name_desc">🔤 이름 역순</option>
                        <option value="date_desc">📅 최신 등록순</option>
                        <option value="date_asc">📅 오래된 등록순</option>
                        <option value="size_desc">💾 파일 크기순</option>
                    </select>
                    <div class="stats" id="stats-badge">불러오는 중...</div>
                </div>
            </div>

            <!-- Media Grid (Folders & Videos) -->
            <div class="video-grid list-view" id="video-grid">
                <div class="loading-spinner">항목을 불러오는 중입니다...</div>
            </div>
        </main>
    </div>

    <!-- Video Player Modal -->
    <div id="player-modal" class="modal">
        <div class="modal-dialog">
            <div class="modal-header" title="마우스로 드래그하여 창 이동 (더블클릭: 중앙 정렬)">
                <h2 id="player-title" class="video-title-display">
                    <span class="drag-handle-icon" title="마우스로 드래그하여 창 이동">✥</span>
                    <span id="player-title-text">제목</span>
                </h2>
                <div class="modal-header-actions">
                    <button id="prev-video-btn" class="btn btn-small" title="이전 영상 재생 (단축키: Shift + P)">⏮️ 이전</button>
                    <button id="next-video-btn" class="btn btn-small" title="다음 영상 재생 (단축키: Shift + N)">다음 ⏭️</button>
                    <button id="fullscreen-btn" class="btn btn-small" title="전체화면 (단축키: F 또는 더블클릭)">⛶ 전체화면</button>
                    <button id="close-player-btn" class="btn-close" title="닫기 (Esc)">&times;</button>
                </div>
            </div>
            <div class="modal-body">
                <div class="video-wrapper" id="video-wrapper">
                    <video id="video-player" playsinline controls preload="metadata"></video>
                    <!-- Custom High-Fidelity Subtitle Overlay -->
                    <div id="subtitle-box" class="subtitle-box" style="display:none;"></div>
                </div>
            </div>
            <!-- Player Toolbar -->
            <div class="modal-footer">
                <div class="control-group">
                    <label for="sub-select">자막 선택:</label>
                    <select id="sub-select" class="select-input">
                        <option value="">자막 없음</option>
                    </select>
                    <button id="custom-sub-btn" class="btn btn-small">📂 외부 자막 열기</button>
                    <input type="file" id="custom-sub-input" accept=".smi,.sami,.srt,.ass,.ssa,.vtt" style="display:none">
                </div>
                <div class="control-group">
                    <span>자막 스타일:</span>
                    <button id="sub-bg-toggle" class="btn btn-small" title="자막 배경 박스 전환 (단축키: B)">🔳 배경: 있음</button>
                    <button id="font-decrease" class="btn btn-small" title="자막 축소 (단축키: -)">A-</button>
                    <button id="font-increase" class="btn btn-small" title="자막 확대 (단축키: +)">A+</button>
                </div>
                <div class="control-group">
                    <span>싱크 조절:</span>
                    <button class="btn btn-small sync-btn" data-offset="-0.5">-0.5s</button>
                    <span id="sync-display" class="sync-value">0.0s</span>
                    <button class="btn btn-small sync-btn" data-offset="0.5">+0.5s</button>
                    <button id="sync-reset" class="btn btn-small">초기화</button>
                </div>

            </div>
            <!-- Floating Player Resize Handle -->
            <div id="modal-resize-handle" class="modal-resize-handle" title="창 크기 조절 (마우스 드래그 / 더블클릭: 기본 크기 복원)">⤡</div>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="toast"></div>

    <script src="app.js"></script>
</body>
</html>
"""

STYLE_CSS = """* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

:root {
    --bg-dark: #0f172a;
    --bg-card: #1e293b;
    --bg-hover: #334155;
    --accent: #38bdf8;
    --accent-hover: #0ea5e9;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
    --badge-ass: #a855f7;
    --badge-smi: #22c55e;
    --badge-srt: #3b82f6;
    --badge-none: #64748b;
    --radius: 10px;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2);
    --sub-scale: 1;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
    background-color: var(--bg-dark);
    color: var(--text-main);
    min-height: 100vh;
}

.app-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

/* Navbar */
.navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    padding: 12px 20px;
    background-color: var(--bg-card);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.brand {
    display: flex;
    align-items: center;
    gap: 10px;
    user-select: none;
}

.brand .icon {
    font-size: 1.8rem;
}

.brand h1 {
    font-size: 1.3rem;
    font-weight: 700;
}

.brand h1 span {
    color: var(--accent);
}

.search-bar {
    flex: 1;
    max-width: 450px;
    position: relative;
    display: flex;
    align-items: center;
}

.search-bar input {
    width: 100%;
    padding: 10px 35px 10px 14px;
    background-color: var(--bg-dark);
    border: 1px solid var(--bg-hover);
    border-radius: 20px;
    color: var(--text-main);
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.2s;
}

.search-bar input:focus {
    border-color: var(--accent);
}

.clear-btn {
    position: absolute;
    right: 12px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 1.2rem;
    cursor: pointer;
    display: none;
}

.nav-actions {
    display: flex;
    gap: 10px;
}

/* Buttons */
.btn {
    padding: 8px 14px;
    border: none;
    border-radius: 6px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: background-color 0.2s, transform 0.1s;
}

.btn:active {
    transform: scale(0.97);
}

.btn-secondary {
    background-color: var(--bg-hover);
    color: var(--text-main);
}

.btn-secondary:hover {
    background-color: #475569;
}

.btn-small {
    padding: 5px 10px;
    font-size: 0.8rem;
    background-color: var(--bg-hover);
    color: var(--text-main);
    border-radius: 5px;
    border: none;
    cursor: pointer;
}

.btn-small:hover {
    background-color: #475569;
}

/* Breadcrumb & Mode Toolbar */
.breadcrumb-container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding: 0 4px;
    flex-wrap: wrap;
    gap: 12px;
}

.breadcrumbs {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95rem;
    flex-wrap: wrap;
}

.crumb {
    color: var(--accent);
    cursor: pointer;
    font-weight: 500;
    transition: color 0.15s;
}

.crumb:hover {
    text-decoration: underline;
    color: var(--accent-hover);
}

.crumb.active {
    color: #cbd5e1;
    cursor: default;
    text-decoration: none;
    font-weight: 700;
}

.crumb-sep {
    color: var(--text-muted);
    user-select: none;
    font-size: 0.85rem;
}

.toolbar-right {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
}

.view-mode-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--bg-hover);
    border-radius: 20px;
    padding: 3px;
    gap: 3px;
}

.btn-mode {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.84rem;
    font-weight: 600;
    padding: 5px 12px;
    border-radius: 16px;
    cursor: pointer;
    transition: background-color 0.2s, color 0.2s;
}

.btn-mode:hover {
    color: var(--text-main);
}

.btn-mode.active {
    background-color: var(--accent);
    color: #0f172a;
    font-weight: 700;
}

.sort-select {
    background-color: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--bg-hover);
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 0.84rem;
    font-weight: 600;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s;
}

.sort-select:hover, .sort-select:focus {
    border-color: var(--accent);
}

.layout-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--bg-hover);
    border-radius: 20px;
    padding: 3px;
    gap: 3px;
}

.btn-layout {
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 0.82rem;
    font-weight: 600;
    padding: 5px 10px;
    border-radius: 16px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: background-color 0.2s, color 0.2s;
}

.btn-layout:hover {
    color: var(--text-main);
}

.btn-layout.active {
    background-color: var(--accent);
    color: #0f172a;
    font-weight: 700;
}

.meta-toggle {
    display: flex;
    background-color: var(--bg-card);
    border: 1px solid var(--bg-hover);
    border-radius: 20px;
    padding: 3px;
    gap: 3px;
}

.toggle-text-short {
    display: none;
}

@media (max-width: 900px) {
    .toggle-text-full {
        display: none;
    }
    .toggle-text-short {
        display: inline;
    }
}

/* Hide file date & size when meta toggle is set to hidden (default) */
.video-grid.hide-file-meta .video-card .card-meta {
    display: none !important;
}

.stats {
    font-size: 0.88rem;
    color: var(--text-muted);
    background: var(--bg-card);
    padding: 6px 14px;
    border-radius: 20px;
    white-space: nowrap;
}

/* Video & Folder Grid */
.video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
}

/* List View Styles */
.video-grid.list-view {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.video-grid.list-view .folder-card,
.video-grid.list-view .video-card {
    flex-direction: row;
    height: 60px;
    min-height: 60px;
    padding: 6px 16px;
    border-radius: 8px;
    align-items: center;
    gap: 15px;
    box-shadow: none;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.video-grid.list-view .folder-thumbnail,
.video-grid.list-view .card-thumbnail {
    width: 44px;
    height: 44px;
    min-width: 44px;
    border-radius: 6px;
}

.video-grid.list-view .folder-icon {
    font-size: 1.5rem;
}

.video-grid.list-view .card-folder-badge,
.video-grid.list-view .card-format-badge {
    display: none;
}

.video-grid.list-view .play-icon-overlay {
    opacity: 0.7;
    font-size: 1.2rem;
    transform: none;
    background: none;
    box-shadow: none;
}

.video-grid.list-view .card-content {
    flex: 1;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    padding: 0;
    gap: 15px;
    overflow: hidden;
}

.video-grid.list-view .list-main-col {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    flex: 1;
}

.video-grid.list-view .card-title {
    font-size: 0.95rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 2px;
}

.video-grid.list-view .card-folder-path {
    font-size: 0.75rem;
    color: var(--accent);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.video-grid.list-view .list-sub-col {
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;
}

.video-grid.list-view .card-meta {
    font-size: 0.8rem;
    display: flex;
    gap: 12px;
    color: var(--text-muted);
    white-space: nowrap;
}

.video-grid.list-view .card-badges {
    display: flex;
    gap: 4px;
    min-width: 60px;
    justify-content: flex-end;
}

/* Cards (Default Grid) */
.folder-card, .video-card {
    background-color: var(--bg-card);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
    transition: transform 0.15s ease, box-shadow 0.15s ease, background-color 0.15s ease;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    border: 1px solid transparent;
}

.folder-card:hover, .video-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -2px rgba(0, 0, 0, 0.4);
    background-color: var(--bg-hover);
    border-color: rgba(56, 189, 248, 0.3);
}

.folder-thumbnail {
    height: 120px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.parent-card .folder-thumbnail {
    background: linear-gradient(135deg, #334155, #1e293b);
}

.folder-icon {
    font-size: 3.5rem;
    opacity: 0.85;
    transition: transform 0.2s;
}

.folder-card:hover .folder-icon {
    transform: scale(1.1);
}

.card-thumbnail {
    height: 150px;
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.play-icon-overlay {
    width: 44px;
    height: 44px;
    background-color: rgba(56, 189, 248, 0.85);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0f172a;
    font-size: 1.2rem;
    padding-left: 3px;
    transition: transform 0.2s, background-color 0.2s;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
}

.video-card:hover .play-icon-overlay {
    transform: scale(1.15);
    background-color: var(--accent);
}

.card-format-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background-color: rgba(15, 23, 42, 0.85);
    color: var(--text-main);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 6px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.card-folder-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background-color: rgba(56, 189, 248, 0.2);
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    padding: 3px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

.card-content {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}

.card-title {
    font-size: 0.92rem;
    font-weight: 600;
    line-height: 1.35;
    word-break: break-all;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.card-meta {
    font-size: 0.78rem;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
}

.card-badges {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
    margin-top: 4px;
}

.badge {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 4px;
    text-transform: uppercase;
}

.badge-smi, .badge-sami {
    background-color: rgba(34, 197, 94, 0.2);
    color: var(--badge-smi);
    border: 1px solid rgba(34, 197, 94, 0.3);
}

.badge-srt, .badge-vtt {
    background-color: rgba(59, 130, 246, 0.2);
    color: var(--badge-srt);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-ass, .badge-ssa {
    background-color: rgba(168, 85, 247, 0.2);
    color: var(--badge-ass);
    border: 1px solid rgba(168, 85, 247, 0.3);
}

.badge-none {
    background-color: rgba(100, 116, 139, 0.2);
    color: var(--badge-none);
}

/* Modal Video Player */
.modal {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    pointer-events: none;
}

.modal.active {
    display: block;
}

.modal-dialog {
    position: fixed;
    width: min(94vw, 1050px);
    min-width: 380px;
    min-height: 250px;
    max-width: 98vw;
    max-height: 96vh;
    background-color: #11151d;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    overflow: hidden;
    box-shadow: 0 25px 65px -10px rgba(0, 0, 0, 0.88), 0 0 0 1px rgba(255, 255, 255, 0.08), 0 10px 30px rgba(0, 0, 0, 0.6);
    display: flex;
    flex-direction: column;
    z-index: 10000;
    pointer-events: auto;
    resize: both;
    contain: layout;
    will-change: width, height;
}

body.is-resizing,
body.is-dragging {
    user-select: none !important;
    -webkit-user-select: none !important;
}

:focus-visible {
    outline: 2px solid #38bdf8 !important;
    outline-offset: 2px !important;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 14px;
    background: linear-gradient(180deg, #1f2633 0%, #171d27 100%);
    border-bottom: 1px solid rgba(255, 255, 255, 0.09);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
    cursor: grab;
    user-select: none;
    touch-action: none;
    gap: 12px;
    min-width: 0;
    flex-shrink: 0;
}

.modal-dialog .btn-small {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.13);
    color: #e2e8f0;
    border-radius: 6px;
    padding: 5px 11px;
    font-size: 0.8rem;
    font-weight: 500;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.modal-dialog .btn-small:hover {
    background-color: rgba(255, 255, 255, 0.16);
    border-color: rgba(255, 255, 255, 0.28);
    color: #ffffff;
    transform: translateY(-1px);
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.35);
}

.modal-dialog .btn-small:active {
    transform: translateY(0);
    background-color: rgba(255, 255, 255, 0.1);
}

.modal-header.dragging {
    cursor: grabbing;
}

.video-title-display {
    font-size: 0.93rem;
    font-weight: 600;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 7px;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    margin-right: 0;
    letter-spacing: -0.01em;
}

#player-title-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    min-width: 0;
    flex: 1;
    display: inline-block;
}

.drag-handle-icon {
    font-size: 1.1rem;
    color: #38bdf8;
    cursor: grab;
    flex-shrink: 0;
    opacity: 0.85;
}

.modal-header-actions {
    display: flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
    white-space: nowrap;
}

.modal-header-actions button,
.modal-header-actions a {
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}

.btn-close {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 1.15rem;
    line-height: 1;
    cursor: pointer;
    padding: 0;
    margin-left: 3px;
    transition: all 0.15s ease;
}

.btn-close:hover {
    background: rgba(239, 68, 68, 0.25);
    border-color: rgba(239, 68, 68, 0.45);
    color: #f87171;
    transform: scale(1.08);
}

/* Video Player Area */
.modal-body {
    background-color: black;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;
    min-height: 0;
    overflow: hidden;
}

.video-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
    flex: 1;
    min-height: 180px;
    aspect-ratio: 16 / 9;
    max-height: calc(96vh - 110px);
    display: flex;
    align-items: center;
    justify-content: center;
    background: black;
}

/* Fullscreen support on video-wrapper */
.video-wrapper:fullscreen,
.video-wrapper:-webkit-full-screen {
    width: 100vw !important;
    height: 100vh !important;
    max-height: 100vh !important;
    background: black !important;
}

.video-wrapper:fullscreen video,
.video-wrapper:-webkit-full-screen video {
    width: 100vw !important;
    height: 100vh !important;
    max-height: 100vh !important;
    object-fit: contain;
}

video {
    width: 100%;
    height: 100%;
    max-height: 100%;
    object-fit: contain;
    background: black;
}

/* Subtitle Overlay Box */
.subtitle-box {
    display: none;
    position: absolute;
    bottom: 55px;
    left: 4%;
    right: 4%;
    text-align: center;
    color: #ffffff;
    font-size: calc(clamp(1.05rem, 1.25rem + 0.3vw, 1.45rem) * var(--sub-scale, 1));
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 2px 2px 4px #000, -2px -2px 4px #000, 2px -2px 4px #000, -2px 2px 4px #000, 0 0 8px #000;
    pointer-events: none;
    user-select: none;
    z-index: 2147483647;
    white-space: pre-wrap;
    transition: font-size 0.1s;
    transform: translateZ(0);
    will-change: transform, opacity;
}

.subtitle-box.pos-top {
    top: 50px !important;
    bottom: auto !important;
}

.subtitle-box span {
    display: inline-block;
    background-color: rgba(0, 0, 0, 0.75);
    padding: 6px 16px;
    border-radius: 6px;
    max-width: 92%;
    word-break: break-word;
}

.subtitle-box.no-bg span {
    background-color: transparent !important;
    text-shadow: 2px 2px 3px #000, -2px -2px 3px #000, 2px -2px 3px #000, -2px 2px 3px #000, 0 0 10px #000, 0 2px 6px #000 !important;
}

.video-wrapper:fullscreen .subtitle-box,
.video-wrapper:-webkit-full-screen .subtitle-box {
    bottom: 95px !important;
    font-size: calc(clamp(2.0rem, 3.0vw, 3.6rem) * var(--sub-scale, 1)) !important;
    z-index: 2147483647 !important;
}

.video-wrapper:fullscreen .subtitle-box.pos-top,
.video-wrapper:-webkit-full-screen .subtitle-box.pos-top {
    top: 60px !important;
    bottom: auto !important;
}

/* Native WebVTT / HTML5 TextTrack Subtitle Styling */
video::cue {
    background-color: rgba(0, 0, 0, 0.75);
    color: #ffffff;
    font-size: 2.8vw;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif;
    font-weight: 700;
    line-height: 1.4;
    text-shadow: 2px 2px 4px #000, -2px -2px 4px #000;
    white-space: pre-line;
}

/* Modal Footer Toolbar */
.modal-footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 14px;
    padding: 9px 16px;
    background: linear-gradient(180deg, #171d27 0%, #11151d 100%);
    border-top: 1px solid rgba(255, 255, 255, 0.09);
    font-size: 0.83rem;
    flex-shrink: 0;
    position: relative;
}

.modal-dialog .select-input {
    background-color: #0d1017;
    color: #f1f5f9;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: border-color 0.15s, box-shadow 0.15s;
}

.modal-dialog .select-input:hover,
.modal-dialog .select-input:focus {
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
    outline: none;
}

.modal-dialog .control-group label,
.modal-dialog .control-group span {
    color: #94a3b8;
    font-size: 0.81rem;
    font-weight: 500;
}

.sync-value {
    min-width: 44px;
    text-align: center;
    font-weight: 700;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 0.78rem;
    letter-spacing: 0.02em;
}

.modal-resize-handle {
    position: absolute;
    right: 3px;
    bottom: 3px;
    width: 20px;
    height: 20px;
    cursor: nwse-resize;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(255, 255, 255, 0.35);
    font-size: 1.05rem;
    line-height: 1;
    user-select: none;
    touch-action: none;
    z-index: 10001;
    transition: color 0.15s, transform 0.15s;
}

.modal-resize-handle:hover,
.modal-resize-handle.resizing {
    color: #38bdf8;
    transform: scale(1.25);
}

.control-group {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.control-group label,
.control-group span {
    white-space: nowrap;
    font-size: 0.82rem;
    color: var(--text-muted);
}

.select-input {
    background: var(--bg-dark);
    color: var(--text-main);
    border: 1px solid var(--bg-hover);
    padding: 4px 8px;
    border-radius: 4px;
    outline: none;
    max-width: 220px;
    min-width: 120px;
    font-size: 0.82rem;
}

.sync-value {
    min-width: 42px;
    text-align: center;
    font-weight: bold;
    color: var(--accent);
}

/* Toast */
.toast {
    position: fixed;
    top: 25px;
    left: 50%;
    transform: translateX(-50%) translateY(-100px);
    background-color: rgba(30, 41, 59, 0.95);
    color: var(--text-main);
    border: 1px solid var(--accent);
    font-weight: 600;
    padding: 9px 20px;
    border-radius: 20px;
    box-shadow: var(--shadow);
    transition: transform 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
    z-index: 99999;
    pointer-events: none;
}

.toast.show {
    transform: translateX(-50%) translateY(0);
}

.loading-spinner {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 0;
    color: var(--text-muted);
    font-size: 1.1rem;
}

/* Responsive Breakpoints & Distorted Window Fixes */
@media (max-width: 960px) {
    .modal-footer {
        justify-content: flex-start;
        gap: 8px 14px;
    }
}

@media (max-width: 768px) {
    .navbar {
        padding: 10px 14px;
        gap: 10px;
    }
    .search-bar {
        order: 3;
        max-width: 100%;
        flex-basis: 100%;
    }
    .brand h1 {
        font-size: 1.15rem;
    }
    .toolbar-right {
        gap: 6px;
    }
    .btn-mode, .btn-layout, .sort-select {
        padding: 4px 8px;
        font-size: 0.78rem;
    }
    .video-grid.list-view .card-meta {
        font-size: 0.72rem;
        gap: 6px;
    }
    .video-grid.list-view .list-sub-col {
        gap: 8px;
    }
}

@media (max-width: 640px) {
    .modal-dialog {
        width: 98vw;
        max-height: 98vh;
    }
    .modal-header-actions .btn-small {
        padding: 4px 6px;
        font-size: 0.76rem;
    }
    .modal-footer {
        padding: 6px 10px;
        gap: 6px 8px;
    }
    .control-group {
        gap: 4px;
    }
    .control-group .btn-small {
        padding: 3px 6px;
        font-size: 0.76rem;
    }
    .select-input {
        max-width: 150px;
        font-size: 0.78rem;
    }
    .subtitle-box {
        font-size: 1.1rem;
        bottom: 40px;
    }
}
"""

APP_JS = """// MyCloud Web Media Player Client App

let currentMode = 'folder'; // 'folder' or 'all'
let currentSort = localStorage.getItem('mycloud_sort_mode') || 'name_asc';
let currentLayout = localStorage.getItem('mycloud_layout_v2') || 'list'; // 'list' or 'grid' (default: list)
let currentDir = '';
let currentParentDir = null;
let currentDirs = [];
let currentVideos = [];
let activeVideo = null;

let parsedSubtitles = []; // array of { start: seconds, end: seconds, text: string, isTop: boolean }
let subtitleOffset = 0; // in seconds
let subScale = 1.0;
let subBgEnabled = localStorage.getItem('mycloud_sub_bg') !== 'false';
let currentAvailableTracks = [];
let currentCueIndex = -1;

// DOM Elements
const videoGrid = document.getElementById('video-grid');
const searchInput = document.getElementById('search-input');
const clearSearchBtn = document.getElementById('clear-search');
const refreshBtn = document.getElementById('refresh-btn');
const statsBadge = document.getElementById('stats-badge');
const breadcrumbsContainer = document.getElementById('breadcrumbs');
const modeFolderBtn = document.getElementById('mode-folder-btn');
const modeAllBtn = document.getElementById('mode-all-btn');
const layoutGridBtn = document.getElementById('layout-grid-btn');
const layoutListBtn = document.getElementById('layout-list-btn');
const metaHideBtn = document.getElementById('meta-hide-btn');
const metaShowBtn = document.getElementById('meta-show-btn');
const sortSelect = document.getElementById('sort-select');

const playerModal = document.getElementById('player-modal');
const closePlayerBtn = document.getElementById('close-player-btn');
const playerTitle = document.getElementById('player-title');
const videoWrapper = document.getElementById('video-wrapper');
const videoPlayer = document.getElementById('video-player');
const subtitleBox = document.getElementById('subtitle-box');
const subSelect = document.getElementById('sub-select');
const customSubBtn = document.getElementById('custom-sub-btn');
const customSubInput = document.getElementById('custom-sub-input');
const fullscreenBtn = document.getElementById('fullscreen-btn');

const syncDisplay = document.getElementById('sync-display');
const syncResetBtn = document.getElementById('sync-reset');
const subBgToggleBtn = document.getElementById('sub-bg-toggle');
const fontDecreaseBtn = document.getElementById('font-decrease');
const fontIncreaseBtn = document.getElementById('font-increase');
const directLinkBtn = document.getElementById('direct-link-btn');
const downloadLink = document.getElementById('download-link');

const modalDialog = document.querySelector('.modal-dialog');
const modalHeader = document.querySelector('.modal-header');
const playerTitleText = document.getElementById('player-title-text');
const resizeHandle = document.getElementById('modal-resize-handle');
const prevVideoBtn = document.getElementById('prev-video-btn');
const nextVideoBtn = document.getElementById('next-video-btn');

let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let initialDialogLeft = 0;
let initialDialogTop = 0;
let hasCustomPosition = false;

function centerModalDialog() {
    if (!modalDialog) return;
    modalDialog.style.margin = '0';
    const dialogWidth = modalDialog.offsetWidth || Math.min(window.innerWidth * 0.94, 1050);
    const dialogHeight = modalDialog.offsetHeight || Math.min(window.innerHeight * 0.88, 620);
    const left = Math.max(10, Math.round((window.innerWidth - dialogWidth) / 2));
    const top = Math.max(10, Math.round((window.innerHeight - dialogHeight) / 2));
    
    modalDialog.style.left = `${left}px`;
    modalDialog.style.top = `${top}px`;
    hasCustomPosition = false;
}

if (videoPlayer) {
    videoPlayer.addEventListener('loadedmetadata', () => {
        if (!hasCustomPosition) {
            centerModalDialog();
        }
    });
}

// Setup Draggable Modal Window via Pointer Events
if (modalHeader && modalDialog) {
    modalHeader.addEventListener('pointerdown', (e) => {
        if (e.target.closest('button, a, input, select')) return;
        
        isDragging = true;
        try { modalHeader.setPointerCapture(e.pointerId); } catch (err) {}
        
        const rect = modalDialog.getBoundingClientRect();
        initialDialogLeft = rect.left;
        initialDialogTop = rect.top;
        dragStartX = e.clientX;
        dragStartY = e.clientY;
        
        modalHeader.classList.add('dragging');
        e.preventDefault();
    });
    
    modalHeader.addEventListener('pointermove', (e) => {
        if (!isDragging) return;
        
        const deltaX = e.clientX - dragStartX;
        const deltaY = e.clientY - dragStartY;
        
        let newLeft = initialDialogLeft + deltaX;
        let newTop = initialDialogTop + deltaY;
        
        const dialogWidth = modalDialog.offsetWidth;
        const dialogHeight = modalDialog.offsetHeight;
        const minLeft = 10;
        const maxLeft = Math.max(10, window.innerWidth - dialogWidth - 10);
        const minTop = 10;
        const maxTop = Math.max(10, window.innerHeight - dialogHeight - 10);
        
        newLeft = Math.max(minLeft, Math.min(maxLeft, newLeft));
        newTop = Math.max(minTop, Math.min(maxTop, newTop));
        
        modalDialog.style.left = `${newLeft}px`;
        modalDialog.style.top = `${newTop}px`;
        hasCustomPosition = true;
    });
    
    const endDrag = (e) => {
        if (!isDragging) return;
        isDragging = false;
        modalHeader.classList.remove('dragging');
        try { modalHeader.releasePointerCapture(e.pointerId); } catch (err) {}
    };
    
    modalHeader.addEventListener('pointerup', endDrag);
    modalHeader.addEventListener('pointercancel', endDrag);
    
    modalHeader.addEventListener('dblclick', (e) => {
        if (e.target.closest('button, a, input, select')) return;
        centerModalDialog();
    });
}

// -------------------------------------------------------------
// Floating Player Resizing Engine & Size Persistence
// -------------------------------------------------------------
let isResizing = false;
let resizeStartX = 0;
let resizeStartY = 0;
let startDialogWidth = 0;
let startDialogHeight = 0;

const savedPlayerWidth = localStorage.getItem('mycloud_player_width');
const savedPlayerHeight = localStorage.getItem('mycloud_player_height');
if (savedPlayerWidth && modalDialog) modalDialog.style.width = savedPlayerWidth;
if (savedPlayerHeight && modalDialog) modalDialog.style.height = savedPlayerHeight;

if (resizeHandle && modalDialog) {
    resizeHandle.addEventListener('pointerdown', (e) => {
        isResizing = true;
        resizeStartX = e.clientX;
        resizeStartY = e.clientY;
        const rect = modalDialog.getBoundingClientRect();
        startDialogWidth = rect.width;
        startDialogHeight = rect.height;
        resizeHandle.classList.add('resizing');
        try { resizeHandle.setPointerCapture(e.pointerId); } catch (err) {}
        e.preventDefault();
        e.stopPropagation();
    });

    resizeHandle.addEventListener('pointermove', (e) => {
        if (!isResizing) return;
        const dx = e.clientX - resizeStartX;
        const dy = e.clientY - resizeStartY;
        
        const minW = Math.min(380, window.innerWidth - 20);
        const maxW = window.innerWidth - 20;
        const minH = 240;
        const maxH = window.innerHeight - 20;
        
        const newW = Math.round(Math.max(minW, Math.min(maxW, startDialogWidth + dx)));
        const newH = Math.round(Math.max(minH, Math.min(maxH, startDialogHeight + dy)));
        
        modalDialog.style.width = `${newW}px`;
        modalDialog.style.height = `${newH}px`;
        localStorage.setItem('mycloud_player_width', `${newW}px`);
        localStorage.setItem('mycloud_player_height', `${newH}px`);
    });

    const endResize = (e) => {
        if (!isResizing) return;
        isResizing = false;
        resizeHandle.classList.remove('resizing');
        document.body.classList.remove('is-resizing');
        try { resizeHandle.releasePointerCapture(e.pointerId); } catch (err) {}
    };

    // Auto-clamp floating dialog when window shrinks (Item 23)
    window.addEventListener('resize', () => {
        if (!modalDialog || !playerModal.classList.contains('active')) return;
        const rect = modalDialog.getBoundingClientRect();
        const maxW = window.innerWidth - 20;
        const maxH = window.innerHeight - 20;
        if (rect.width > maxW) modalDialog.style.width = `${maxW}px`;
        if (rect.height > maxH) modalDialog.style.height = `${maxH}px`;
        if (rect.right > window.innerWidth || rect.bottom > window.innerHeight) {
            centerModalDialog();
        }
    });

    resizeHandle.addEventListener('pointerup', endResize);
    resizeHandle.addEventListener('pointercancel', endResize);

    // Double-click resize handle to reset to default size
    resizeHandle.addEventListener('dblclick', (e) => {
        e.stopPropagation();
        modalDialog.style.width = '';
        modalDialog.style.height = '';
        localStorage.removeItem('mycloud_player_width');
        localStorage.removeItem('mycloud_player_height');
        centerModalDialog();
        showToast('창 크기가 기본값으로 초기화되었습니다.');
    });
}

// -------------------------------------------------------------
// Auto Next Video & Playlist Navigation
// -------------------------------------------------------------
function playNextVideo() {
    const sortedVideos = getSortedVideos(currentVideos, currentSort);
    if (!sortedVideos || sortedVideos.length === 0 || !activeVideo) return;
    
    const currentIndex = sortedVideos.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const nextIndex = currentIndex + 1;
    if (nextIndex < sortedVideos.length) {
        const nextVideo = sortedVideos[nextIndex];
        showToast(`⏭️ 다음 영상 자동 재생: ${nextVideo.name}`);
        openPlayer(encodeURIComponent(nextVideo.rel_path));
    } else {
        showToast('🏁 마지막 영상입니다.');
    }
}

function playPrevVideo() {
    const sortedVideos = getSortedVideos(currentVideos, currentSort);
    if (!sortedVideos || sortedVideos.length === 0 || !activeVideo) return;
    
    const currentIndex = sortedVideos.findIndex(v => v.rel_path === activeVideo.rel_path);
    if (currentIndex === -1) return;
    
    const prevIndex = currentIndex - 1;
    if (prevIndex >= 0) {
        const prevVideo = sortedVideos[prevIndex];
        showToast(`⏮️ 이전 영상 재생: ${prevVideo.name}`);
        openPlayer(encodeURIComponent(prevVideo.rel_path));
    } else {
        showToast('첫 번째 영상입니다.');
    }
}

// Auto-play next video when current video ends!
videoPlayer.addEventListener('ended', () => {
    playNextVideo();
});

if (prevVideoBtn) prevVideoBtn.addEventListener('click', playPrevVideo);
if (nextVideoBtn) nextVideoBtn.addEventListener('click', playNextVideo);

function isFullscreen() {
    return !!(document.fullscreenElement || document.webkitFullscreenElement);
}

function enterFullscreenSafe(elem = videoPlayer) {
    const target = elem || videoPlayer;
    if (target.requestFullscreen) {
        target.requestFullscreen().catch(() => {});
    } else if (target.webkitRequestFullscreen) {
        target.webkitRequestFullscreen();
    }
}

function exitFullscreenSafe() {
    if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
    }
}

// Fullscreen toggle on videoPlayer
function toggleFullscreen() {
    if (isFullscreen()) {
        exitFullscreenSafe();
    } else {
        enterFullscreenSafe(videoPlayer);
    }
}

// -------------------------------------------------------------
// Subtitle Display Engine (Dual: High-Fidelity Overlay + Native TextTrack)
// -------------------------------------------------------------
function syncCuesToTextTrack() {
    if (!videoPlayer) return;
    let track = null;
    if (videoPlayer.textTracks) {
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            if (videoPlayer.textTracks[i].label === 'WebPlayerSub') {
                track = videoPlayer.textTracks[i];
                break;
            }
        }
    }
    if (!track) {
        try {
            track = videoPlayer.addTextTrack("subtitles", "WebPlayerSub", "ko");
        } catch (e) {
            return;
        }
    }
    
    const isFs = isFullscreen();
    track.mode = isFs ? "showing" : "hidden";
    
    if (track.cues) {
        while (track.cues.length > 0) {
            track.removeCue(track.cues[0]);
        }
    }
    
    parsedSubtitles.forEach(c => {
        try {
            const plainText = c.text.replace(/<br\\s*\\/?>/gi, '\\n');
            const startTime = Math.max(0, c.start + subtitleOffset);
            const endTime = Math.max(startTime + 0.1, c.end + subtitleOffset);
            const cue = new VTTCue(startTime, endTime, plainText);
            cue.snapToLines = false;
            if (c.isTop) {
                cue.line = 8;
            } else {
                cue.line = 90;
            }
            cue.position = 50;
            track.addCue(cue);
        } catch (e) {}
    });
}

function handleFullscreenSubtitleSync() {
    let track = null;
    if (videoPlayer && videoPlayer.textTracks) {
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            if (videoPlayer.textTracks[i].label === 'WebPlayerSub') {
                track = videoPlayer.textTracks[i];
                break;
            }
        }
    }
    
    const isFs = isFullscreen();
    if (isFs) {
        // Native video element fullscreen: show native WebVTT cues mirroring custom settings
        if (track) track.mode = "showing";
        if (subtitleBox) subtitleBox.style.display = "none";
    } else {
        // Windowed floating player: hide native cues, show rich DOM overlay
        if (track) track.mode = "hidden";
        updateSubtitleDisplay();
    }
    applySubtitleStyle();
}

function handleFullscreenChange() {
    const fsElem = document.fullscreenElement || document.webkitFullscreenElement;
    
    // Update Fullscreen button text in modal header
    if (fullscreenBtn) {
        const isFs = !!fsElem;
        fullscreenBtn.innerHTML = isFs ? '🗗 전체화면 해제' : '⛶ 전체화면';
        fullscreenBtn.title = isFs ? '전체화면 해제 (단축키: F 또는 Esc)' : '전체화면 (단축키: F 또는 더블클릭)';
    }
    
    handleFullscreenSubtitleSync();
}

document.addEventListener('fullscreenchange', handleFullscreenChange);
document.addEventListener('webkitfullscreenchange', handleFullscreenChange);

let lastDisplayedText = null;
let lastDisplayedPosTop = null;

function updateSubtitleDisplay() {
    if (!subtitleBox) return;
    
    const fsElem = document.fullscreenElement || document.webkitFullscreenElement;
    if (fsElem === videoPlayer) {
        if (subtitleBox.style.display !== 'none') subtitleBox.style.display = 'none';
        return;
    }
    
    if (parsedSubtitles.length === 0) {
        if (lastDisplayedText !== '') {
            subtitleBox.style.display = 'none';
            subtitleBox.innerHTML = '';
            lastDisplayedText = '';
            lastDisplayedPosTop = false;
        }
        currentCueIndex = -1;
        return;
    }
    
    const curTime = videoPlayer.currentTime + subtitleOffset;
    let textToDisplay = '';
    let isTop = false;
    
    // Fast boundary search on sorted parsedSubtitles
    for (let i = 0; i < parsedSubtitles.length; i++) {
        const c = parsedSubtitles[i];
        if (curTime < c.start) {
            if (c.start - curTime > 20) break;
            continue;
        }
        if (curTime <= c.end) {
            if (c.isTop) {
                isTop = true;
            }
            textToDisplay = textToDisplay ? textToDisplay + '<br>' + c.text : c.text;
        }
    }
    
    if (textToDisplay) {
        if (textToDisplay !== lastDisplayedText || isTop !== lastDisplayedPosTop) {
            if (isTop) subtitleBox.classList.add('pos-top');
            else subtitleBox.classList.remove('pos-top');
            subtitleBox.innerHTML = `<span>${textToDisplay}</span>`;
            subtitleBox.style.display = 'block';
            lastDisplayedText = textToDisplay;
            lastDisplayedPosTop = isTop;
        }
    } else {
        if (lastDisplayedText !== '') {
            subtitleBox.style.display = 'none';
            subtitleBox.innerHTML = '';
            lastDisplayedText = '';
            lastDisplayedPosTop = false;
        }
    }
}

if (videoPlayer) {
    videoPlayer.addEventListener('timeupdate', updateSubtitleDisplay);
    videoPlayer.addEventListener('seeked', updateSubtitleDisplay);
    videoPlayer.addEventListener('seeking', updateSubtitleDisplay);
    videoPlayer.addEventListener('pause', updateSubtitleDisplay);
    videoPlayer.addEventListener('play', updateSubtitleDisplay);
}

// -------------------------------------------------------------
// 1. Fetch and Load Directory Data
// -------------------------------------------------------------
async function loadData(dir = currentDir, mode = currentMode) {
    currentMode = mode;
    currentDir = dir;
    
    if (modeFolderBtn && modeAllBtn) {
        modeFolderBtn.classList.toggle('active', currentMode === 'folder');
        modeAllBtn.classList.toggle('active', currentMode === 'all');
    }
    
    videoGrid.innerHTML = '<div class="loading-spinner">항목을 불러오는 중입니다...</div>';
    
    try {
        let apiUrl = 'api.php';
        if (currentMode === 'all') {
            apiUrl += '?all=1';
        } else if (dir) {
            apiUrl += '?dir=' + encodeURIComponent(dir);
        }
        
        const resp = await fetch(apiUrl);
        const data = await resp.json();
        
        if (!data.success) {
            videoGrid.innerHTML = `<div class="loading-spinner">오류: ${data.error}</div>`;
            return;
        }
        
        currentVideos = data.videos || [];
        currentDirs = data.dirs || [];
        currentParentDir = data.parent_dir !== undefined ? data.parent_dir : null;
        
        updateBreadcrumbs();
        updateStats();
        applySortAndRender();
        
        if (searchInput.value) {
            searchInput.value = '';
            clearSearchBtn.style.display = 'none';
        }
    } catch (err) {
        videoGrid.innerHTML = `<div class="loading-spinner">서버 연결 실패: ${err.message}</div>`;
    }
}

function updateBreadcrumbs() {
    if (!breadcrumbsContainer) return;
    
    if (currentMode === 'all') {
        breadcrumbsContainer.innerHTML = `
            <span class="crumb" onclick="switchMode('folder', '')">🏠 Public</span>
            <span class="crumb-sep">›</span>
            <span class="crumb active">🎬 전체 영상 모아보기</span>
        `;
        return;
    }
    
    if (!currentDir) {
        breadcrumbsContainer.innerHTML = `<span class="crumb active" data-path="">🏠 Public</span>`;
        return;
    }
    
    const parts = currentDir.split('/');
    let html = `<span class="crumb" onclick="openFolder('')">🏠 Public</span>`;
    let accumulated = '';
    
    parts.forEach((p, idx) => {
        accumulated = accumulated ? accumulated + '/' + p : p;
        html += `<span class="crumb-sep">›</span>`;
        if (idx === parts.length - 1) {
            html += `<span class="crumb active">${escapeHtml(p)}</span>`;
        } else {
            html += `<span class="crumb" onclick="openFolder('${encodeURIComponent(accumulated)}')">${escapeHtml(p)}</span>`;
        }
    });
    
    breadcrumbsContainer.innerHTML = html;
}

function updateStats() {
    if (currentMode === 'all') {
        const subCount = currentVideos.filter(v => v.subtitles && v.subtitles.length > 0).length;
        statsBadge.textContent = `전체 영상 ${currentVideos.length}개 (외부자막: ${subCount}개)`;
    } else {
        const dCount = currentDirs.length;
        const vCount = currentVideos.length;
        statsBadge.textContent = `폴더 ${dCount}개 · 동영상 ${vCount}개`;
    }
}

// -------------------------------------------------------------
// 2. Sorting & Grid Rendering
// -------------------------------------------------------------
function getSortedVideos(videos, sortMode) {
    const copy = [...videos];
    switch (sortMode) {
        case 'name_asc':
            return copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
        case 'name_desc':
            return copy.sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: 'base' }));
        case 'date_desc':
            return copy.sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
        case 'date_asc':
            return copy.sort((a, b) => (a.mtime || 0) - (b.mtime || 0));
        case 'size_desc':
            return copy.sort((a, b) => (b.size || 0) - (a.size || 0));
        default:
            return copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
    }
}

function getSortedDirs(dirs, sortMode) {
    const copy = [...dirs];
    if (sortMode === 'name_desc') {
        return copy.sort((a, b) => b.name.localeCompare(a.name, undefined, { numeric: true, sensitivity: 'base' }));
    }
    return copy.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
}

function applySortAndRender() {
    const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    let targetVideos = getSortedVideos(currentVideos, currentSort);
    let targetDirs = getSortedDirs(currentDirs, currentSort);
    
    if (query) {
        if (currentMode === 'all') {
            targetVideos = targetVideos.filter(v => 
                v.name.toLowerCase().includes(query) || (v.folder && v.folder.toLowerCase().includes(query))
            );
            renderGrid([], targetVideos);
            return;
        } else {
            targetDirs = targetDirs.filter(d => d.name.toLowerCase().includes(query));
            targetVideos = targetVideos.filter(v => v.name.toLowerCase().includes(query));
            
            if (targetDirs.length === 0 && targetVideos.length === 0) {
                videoGrid.innerHTML = `
                    <div class="loading-spinner">
                        현재 폴더에 '<strong>${escapeHtml(query)}</strong>' 검색 결과가 없습니다.<br><br>
                        <button onclick="switchMode('all'); searchInput.value='${escapeHtml(query)}'; applySortAndRender();" class="btn btn-secondary">
                            🎬 전체 영상 모아보기에서 검색하기
                        </button>
                    </div>
                `;
                return;
            }
        }
    }
    
    renderGrid(targetDirs, targetVideos);
}

if (sortSelect) {
    sortSelect.value = currentSort;
    sortSelect.addEventListener('change', () => {
        currentSort = sortSelect.value;
        localStorage.setItem('mycloud_sort_mode', currentSort);
        applySortAndRender();
    });
}

function setLayoutMode(mode) {
    currentLayout = mode;
    localStorage.setItem('mycloud_layout_v2', mode);
    if (layoutGridBtn && layoutListBtn) {
        layoutGridBtn.classList.toggle('active', mode === 'grid');
        layoutListBtn.classList.toggle('active', mode === 'list');
    }
    if (videoGrid) {
        videoGrid.classList.toggle('list-view', mode === 'list');
    }
}

if (layoutGridBtn) {
    layoutGridBtn.addEventListener('click', () => setLayoutMode('grid'));
}
if (layoutListBtn) {
    layoutListBtn.addEventListener('click', () => setLayoutMode('list'));
}

// File Date and Size Visibility Toggle (Default: Hidden)
let showFileMeta = localStorage.getItem('mycloud_show_file_meta') === 'true'; // defaults to false (hidden)

function applyMetaVisibility() {
    if (showFileMeta) {
        videoGrid.classList.remove('hide-file-meta');
        if (metaHideBtn) metaHideBtn.classList.remove('active');
        if (metaShowBtn) metaShowBtn.classList.add('active');
    } else {
        videoGrid.classList.add('hide-file-meta');
        if (metaHideBtn) metaHideBtn.classList.add('active');
        if (metaShowBtn) metaShowBtn.classList.remove('active');
    }
}

// Initial apply
applyMetaVisibility();

if (metaHideBtn) {
    metaHideBtn.addEventListener('click', () => {
        showFileMeta = false;
        localStorage.setItem('mycloud_show_file_meta', 'false');
        applyMetaVisibility();
        showToast('파일 날짜 및 용량을 숨겼습니다.');
    });
}
if (metaShowBtn) {
    metaShowBtn.addEventListener('click', () => {
        showFileMeta = true;
        localStorage.setItem('mycloud_show_file_meta', 'true');
        applyMetaVisibility();
        showToast('파일 날짜 및 용량을 표시합니다.');
    });
}

function renderGrid(dirs, videos) {
    if ((!dirs || dirs.length === 0) && (!videos || videos.length === 0)) {
        let emptyHtml = '<div class="loading-spinner">표시할 항목이 없습니다.';
        if (currentMode === 'folder' && currentParentDir !== null) {
            emptyHtml += `<br><br><button onclick="openFolder('${encodeURIComponent(currentParentDir)}')" class="btn btn-secondary">⬆️ 상위 폴더로 이동</button>`;
        }
        emptyHtml += '</div>';
        videoGrid.innerHTML = emptyHtml;
        return;
    }
    
    let html = '';
    
    if (currentMode === 'folder' && currentParentDir !== null) {
        html += `
            <div class="folder-card parent-card" onclick="openFolder('${encodeURIComponent(currentParentDir)}')">
                <div class="folder-thumbnail">
                    <span class="card-folder-badge">상위</span>
                    <div class="folder-icon">⬆️</div>
                </div>
                <div class="card-content">
                    <div class="list-main-col">
                        <div class="card-title">.. (상위 폴더로 이동)</div>
                    </div>
                    <div class="list-sub-col">
                        <div class="card-meta">
                            <span>클릭 시 이전 폴더로 이동</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    if (dirs && dirs.length > 0) {
        dirs.forEach(d => {
            let metaDesc = '📁 폴더';
            if (d.video_count > 0 && d.subdir_count > 0) {
                metaDesc = `🎬 영상 ${d.video_count}개 · 📁 ${d.subdir_count}개`;
            } else if (d.video_count > 0) {
                metaDesc = `🎬 영상 ${d.video_count}개`;
            } else if (d.subdir_count > 0) {
                metaDesc = `📁 하위 폴더 ${d.subdir_count}개`;
            }
            
            html += `
                <div class="folder-card" onclick="openFolder('${encodeURIComponent(d.rel_path)}')">
                    <div class="folder-thumbnail">
                        <span class="card-folder-badge">폴더</span>
                        <div class="folder-icon">📁</div>
                    </div>
                    <div class="card-content">
                        <div class="list-main-col">
                            <div class="card-title" title="${escapeHtml(d.name)}">${escapeHtml(d.name)}</div>
                        </div>
                        <div class="list-sub-col">
                            <div class="card-meta">
                                <span>${metaDesc}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    if (videos && videos.length > 0) {
        videos.forEach(v => {
            let badgesHtml = '';
            if (v.subtitles && v.subtitles.length > 0) {
                badgesHtml = v.subtitles.map(s => `<span class="badge badge-${s.ext}">${s.ext.toUpperCase()}</span>`).join('');
            } else if (v.ext === 'mkv' || v.ext === 'mp4') {
                badgesHtml = '<span class="badge badge-srt">내장자막지원</span>';
            } else {
                badgesHtml = '<span class="badge badge-none">자막없음</span>';
            }
            
            const folderTag = (currentMode === 'all' && v.folder)
                ? `<div class="card-folder-path" title="${escapeHtml(v.folder)}">📁 ${escapeHtml(v.folder)}</div>`
                : '';
                
            html += `
                <div class="video-card" onclick="openPlayer('${encodeURIComponent(v.rel_path)}')">
                    <div class="card-thumbnail">
                        <span class="card-format-badge">${v.ext}</span>
                        <div class="play-icon-overlay">▶</div>
                    </div>
                    <div class="card-content">
                        <div class="list-main-col">
                            ${folderTag}
                            <div class="card-title" title="${escapeHtml(v.name)}">${escapeHtml(v.name)}</div>
                        </div>
                        <div class="list-sub-col">
                            <div class="card-meta">
                                <span class="meta-size">💾 ${v.size_formatted}</span>
                                <span class="meta-date">📅 ${(v.mtime_formatted || '').split(' ')[0]}</span>
                            </div>
                            <div class="card-badges">
                                ${badgesHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    }
    
    videoGrid.innerHTML = html;
    applyMetaVisibility();
}

window.openFolder = function(encodedPath) {
    const path = decodeURIComponent(encodedPath);
    loadData(path, 'folder');
};

window.switchMode = function(mode, dir = '') {
    loadData(dir, mode);
};

if (modeFolderBtn) {
    modeFolderBtn.addEventListener('click', () => switchMode('folder', currentDir));
}
if (modeAllBtn) {
    modeAllBtn.addEventListener('click', () => switchMode('all', ''));
}

// -------------------------------------------------------------
// 3. Open Video Player & Subtitle Management
// -------------------------------------------------------------
window.openPlayer = async function(encodedRelPath) {
    const relPath = decodeURIComponent(encodedRelPath);
    const video = currentVideos.find(v => v.rel_path === relPath);
    if (!video) return;
    
    activeVideo = video;
    if (playerTitleText) {
        playerTitleText.textContent = video.name;
    } else if (playerTitle) {
        playerTitle.textContent = video.name;
    }
    if (downloadLink) downloadLink.href = video.url;
    videoPlayer.src = video.url;
    
    clearSubtitles();
    
    // 1. Add external subtitles to list
    currentAvailableTracks = [];
    if (video.subtitles && video.subtitles.length > 0) {
        video.subtitles.forEach(s => {
            currentAvailableTracks.push({
                type: 'external',
                label: `[외부-${s.ext.toUpperCase()}] ${s.filename}`,
                url: s.url,
                ext: s.ext,
                lang: s.ext
            });
        });
    }
    
    renderSubtitleDropdown(currentAvailableTracks, '⏳ 내장 자막 확인 중...');
    
    playerModal.classList.add('active');
    applySubtitleStyle();
    
    if (!hasCustomPosition) {
        centerModalDialog();
        requestAnimationFrame(() => centerModalDialog());
    }
    
    videoPlayer.play().catch(() => {});
    
    // 2. Probe embedded subtitle tracks with AbortController and race condition guard
    if (currentProbeAbortController) {
        currentProbeAbortController.abort();
    }
    if (currentSubAbortController) {
        currentSubAbortController.abort();
    }
    currentProbeAbortController = new AbortController();
    const probeSignal = currentProbeAbortController.signal;
    
    try {
        const probeResp = await fetch(`api.php?action=probe_subs&video=${encodeURIComponent(video.rel_path)}`, { signal: probeSignal });
        const probeData = await probeResp.json();
        
        // Guard against race condition: ensure this response matches active video
        if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
        
        if (probeData.success && probeData.subtitles && probeData.subtitles.length > 0) {
            probeData.subtitles.forEach(emb => {
                currentAvailableTracks.push({
                    type: 'embedded',
                    label: emb.label,
                    streamId: emb.stream_id,
                    codec: emb.codec,
                    lang: emb.lang,
                    relPath: video.rel_path
                });
            });
        }
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.warn('Subtitle probe failed:', e);
        }
    }
    
    if (!activeVideo || activeVideo.rel_path !== video.rel_path) return;
    renderSubtitleDropdown(currentAvailableTracks, null);
    
    // 3. Auto-select Korean subtitle if available
    if (currentAvailableTracks.length > 0) {
        let bestTrack = currentAvailableTracks.find(t => 
            t.lang === 'kor' || t.lang === 'ko' || t.label.includes('한국어')
        );
        if (!bestTrack) {
            bestTrack = currentAvailableTracks[0];
        }
        const bestIdx = currentAvailableTracks.indexOf(bestTrack);
        subSelect.value = String(bestIdx);
        loadSelectedTrack(bestTrack);
    }
};

function renderSubtitleDropdown(tracks, loadingNotice) {
    subSelect.innerHTML = '';
    
    const offOpt = document.createElement('option');
    offOpt.value = '';
    offOpt.textContent = '자막 없음 (끄기)';
    subSelect.appendChild(offOpt);
    
    if (loadingNotice) {
        const noticeOpt = document.createElement('option');
        noticeOpt.value = '__loading__';
        noticeOpt.disabled = true;
        noticeOpt.textContent = loadingNotice;
        subSelect.appendChild(noticeOpt);
    }
    
    tracks.forEach((t, idx) => {
        const opt = document.createElement('option');
        opt.value = String(idx);
        opt.textContent = t.label;
        subSelect.appendChild(opt);
    });
}

const subtitleMemoryCache = new Map();
let currentProbeAbortController = null;
let currentSubAbortController = null;

async function loadSelectedTrack(track) {
    clearSubtitles();
    if (!track) return;
    
    const cacheKey = `${track.relPath || track.url}:${track.streamId !== undefined ? track.streamId : ''}`;
    if (subtitleMemoryCache.has(cacheKey)) {
        parsedSubtitles = subtitleMemoryCache.get(cacheKey);
        syncCuesToTextTrack();
        updateSubtitleDisplay();
        showToast(`⚡ 자막 즉시 로드 완료 (${parsedSubtitles.length}개 자막)`);
        return;
    }
    
    if (currentSubAbortController) {
        currentSubAbortController.abort();
    }
    currentSubAbortController = new AbortController();
    const currentSignal = currentSubAbortController.signal;
    
    try {
        const isEmbedded = (track.type === 'embedded');
        const isAss = (track.codec && track.codec.toLowerCase() === 'ass') || 
                      (track.ext && (track.ext.toLowerCase() === 'ass' || track.ext.toLowerCase() === 'ssa'));
        const isSami = track.ext && (track.ext.toLowerCase() === 'smi' || track.ext.toLowerCase() === 'sami');
        
        showToast(`⏳ [${track.label}] 실시간 읽는 중...`);
        
        const url = isEmbedded
            ? `api.php?action=stream_sub&video=${encodeURIComponent(track.relPath)}&stream=${track.streamId}&codec=${encodeURIComponent(track.codec)}`
            : track.url;
            
        const resp = await fetch(url, { signal: currentSignal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        
        if (!resp.body || isSami) {
            const buffer = await resp.arrayBuffer();
            const text = decodeSubtitleBuffer(buffer);
            if (isAss) parsedSubtitles = parseASS(text);
            else if (isSami) parsedSubtitles = parseSAMI(text);
            else parsedSubtitles = parseSRT(text);
            
            if (parsedSubtitles.length > 0) {
                subtitleMemoryCache.set(cacheKey, parsedSubtitles);
            }
            syncCuesToTextTrack();
            updateSubtitleDisplay();
            showToast(`✅ 자막 로드 완료 (${parsedSubtitles.length}개 자막)`);
            return;
        }
        
        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let rawBuffer = '';
        let lastReportedCount = 0;
        let updateTimer = null;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            rawBuffer += decoder.decode(value, { stream: true });
            
            if (isAss) {
                parsedSubtitles = parseASS(rawBuffer);
            } else {
                parsedSubtitles = parseSRT(rawBuffer);
            }
            
            if (parsedSubtitles.length !== lastReportedCount) {
                lastReportedCount = parsedSubtitles.length;
                syncCuesToTextTrack();
                updateSubtitleDisplay();
                
                if (!updateTimer) {
                    updateTimer = setTimeout(() => {
                        updateTimer = null;
                        if (parsedSubtitles.length > 0 && !currentSignal.aborted) {
                            showToast(`⏳ 자막 실시간 읽는 중... (${parsedSubtitles.length}개)`);
                        }
                    }, 800);
                }
            }
        }
        
        rawBuffer += decoder.decode();
        if (isAss) parsedSubtitles = parseASS(rawBuffer);
        else parsedSubtitles = parseSRT(rawBuffer);
        
        if (parsedSubtitles.length > 0) {
            subtitleMemoryCache.set(cacheKey, parsedSubtitles);
        }
        
        syncCuesToTextTrack();
        updateSubtitleDisplay();
        showToast(`✅ 자막 로드 완료 (${parsedSubtitles.length}개 자막)`);
        
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('Failed to load subtitle:', err);
        showToast(`❌ 자막 로드 실패: ${err.message}`);
    }
}

function clearSubtitles() {
    if (currentSubAbortController) {
        try { currentSubAbortController.abort(); } catch (e) {}
        currentSubAbortController = null;
    }
    parsedSubtitles = [];
    currentCueIndex = -1;
    if (subtitleBox) {
        subtitleBox.innerHTML = '';
        subtitleBox.style.display = 'none';
    }
    subtitleOffset = 0;
    if (syncDisplay) syncDisplay.textContent = '0.0s';
    
    if (videoPlayer && videoPlayer.textTracks) {
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            const track = videoPlayer.textTracks[i];
            if (track.label === 'WebPlayerSub' && track.cues) {
                while (track.cues.length > 0) {
                    track.removeCue(track.cues[0]);
                }
            }
        }
    }
}

subSelect.addEventListener('change', () => {
    const val = subSelect.value;
    if (val === '' || val === '__loading__') {
        clearSubtitles();
    } else {
        const idx = parseInt(val, 10);
        if (currentAvailableTracks[idx]) {
            loadSelectedTrack(currentAvailableTracks[idx]);
        }
    }
});

// -------------------------------------------------------------
// 4. Subtitle Parsers (SRT, ASS, SAMI)
// -------------------------------------------------------------
function decodeSubtitleBuffer(buffer) {
    try {
        const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
        return utf8Decoder.decode(buffer);
    } catch (e) {
        try {
            const eucDecoder = new TextDecoder('euc-kr');
            return eucDecoder.decode(buffer);
        } catch (e2) {
            const fallback = new TextDecoder('utf-8');
            return fallback.decode(buffer);
        }
    }
}

function parseTimestamp(str) {
    if (!str) return 0;
    const parts = str.trim().replace(',', '.').split(':');
    if (parts.length === 3) {
        return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
    } else if (parts.length === 2) {
        return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    }
    return parseFloat(parts[0]) || 0;
}

function parseSRT(srtText) {
    const cues = [];
    const normalized = srtText.replace(/\\r\\n|\\r/g, '\\n');
    const blocks = normalized.split('\\n\\n');
    
    for (const block of blocks) {
        const lines = block.trim().split('\\n');
        if (lines.length >= 2) {
            const timeLine = lines[0].includes('-->') ? lines[0] : lines[1];
            const textLines = lines[0].includes('-->') ? lines.slice(1) : lines.slice(2);
            
            const times = timeLine.split('-->');
            if (times.length === 2) {
                const start = parseTimestamp(times[0].trim());
                const end = parseTimestamp(times[1].trim());
                
                let rawText = textLines.join('\\n');
                const isTop = rawText.includes('{\\\\an8}') || rawText.includes('{\\\\an7}') || rawText.includes('{\\\\an9}');
                
                let cleanText = rawText
                    .replace(/\\{[^}]+\\}/g, '')
                    .replace(/<[^>]+>/g, '')
                    .trim()
                    .replace(/\\n/g, '<br>');
                    
                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    cues.sort((a, b) => a.start - b.start);
    return cues;
}

function parseASS(assText) {
    const cues = [];
    const lines = assText.replace(/\\r\\n|\\r/g, '\\n').split('\\n');
    for (const line of lines) {
        if (line.startsWith('Dialogue:')) {
            const commaIdx = line.indexOf(':');
            const parts = line.substring(commaIdx + 1).split(',');
            if (parts.length >= 10) {
                const start = parseTimestamp(parts[1].trim());
                const end = parseTimestamp(parts[2].trim());
                const rawText = parts.slice(9).join(',');
                
                const isTop = rawText.includes('{\\\\an8}') || rawText.includes('{\\\\an7}') || rawText.includes('{\\\\an9}');
                
                let cleanText = rawText
                    .replace(/\\{[^}]+\\}/g, '')
                    .replace(/\\\\N/g, '<br>')
                    .replace(/\\\\n/g, '<br>')
                    .replace(/\\\\h/g, '&nbsp;')
                    .trim();
                    
                if (cleanText && end > start) {
                    cues.push({ start, end, text: cleanText, isTop });
                }
            }
        }
    }
    cues.sort((a, b) => a.start - b.start);
    return cues;
}

function parseSAMI(smiText) {
    const cues = [];
    const syncRegex = /<SYNC\\s+Start=([0-9]+)[^>]*>([\\s\\S]*?)(?=<SYNC|$)/gi;
    let match;
    
    while ((match = syncRegex.exec(smiText)) !== null) {
        const startSec = parseInt(match[1], 10) / 1000;
        let content = match[2];
        
        content = content.replace(/<P[^>]*>/gi, '')
                         .replace(/<br\\s*\\/?>/gi, '<br>')
                         .replace(/<[^>]+>/g, '')
                         .replace(/&nbsp;/gi, ' ')
                         .trim();
                         
        if (content) {
            cues.push({
                start: startSec,
                end: startSec + 4,
                text: content,
                isTop: false
            });
        } else if (cues.length > 0) {
            const prev = cues[cues.length - 1];
            if (startSec > prev.start) {
                prev.end = startSec;
            }
        }
    }
    
    for (let i = 0; i < cues.length - 1; i++) {
        if (cues[i].end > cues[i + 1].start) {
            cues[i].end = cues[i + 1].start;
        }
    }
    
    return cues;
}

// -------------------------------------------------------------
// 5. Controls & Styling
// -------------------------------------------------------------
function applySubtitleStyle() {
    // 1. Floating player DOM subtitle box
    if (subtitleBox) {
        if (subBgEnabled) {
            subtitleBox.classList.remove('no-bg');
        } else {
            subtitleBox.classList.add('no-bg');
        }
    }
    if (subBgToggleBtn) {
        subBgToggleBtn.textContent = subBgEnabled ? '🔳 배경: 있음' : '🔲 배경: 없음';
    }
    
    // 2. Set root CSS variable for windowed subtitle box
    document.documentElement.style.setProperty('--sub-scale', subScale);
    
    // 3. Dynamic stylesheet for fullscreen video::cue to follow all subtitle settings identically!
    let cueStyleEl = document.getElementById('webplayer-cue-dynamic-style');
    if (!cueStyleEl) {
        cueStyleEl = document.createElement('style');
        cueStyleEl.id = 'webplayer-cue-dynamic-style';
        document.head.appendChild(cueStyleEl);
    }
    
    const cueFontSize = (2.8 * subScale).toFixed(2);
    const cueBg = subBgEnabled 
        ? 'rgba(0, 0, 0, 0.75)' 
        : 'transparent';
    const cueShadow = subBgEnabled
        ? '2px 2px 4px #000, -2px -2px 4px #000, 2px -2px 4px #000, -2px 2px 4px #000, 0 0 8px #000'
        : '2px 2px 3px #000, -2px -2px 3px #000, 2px -2px 3px #000, -2px 2px 3px #000, 0 0 10px #000, 0 2px 6px #000';
        
    cueStyleEl.textContent = `
        video::cue {
            background-color: ${cueBg} !important;
            color: #ffffff !important;
            font-size: ${cueFontSize}vw !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", sans-serif !important;
            font-weight: 700 !important;
            line-height: 1.4 !important;
            text-shadow: ${cueShadow} !important;
            white-space: pre-line !important;
        }
    `;
}

function updateSubtitleScale(newScale) {
    subScale = Math.max(0.6, Math.min(3.0, newScale));
    localStorage.setItem('mycloud_sub_scale', subScale);
    applySubtitleStyle();
}

if (subBgToggleBtn) {
    subBgToggleBtn.addEventListener('click', () => {
        subBgEnabled = !subBgEnabled;
        localStorage.setItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
        applySubtitleStyle();
    });
}

fontIncreaseBtn.addEventListener('click', () => {
    updateSubtitleScale(subScale + 0.15);
});

fontDecreaseBtn.addEventListener('click', () => {
    updateSubtitleScale(subScale - 0.15);
});

document.querySelectorAll('.sync-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const offset = parseFloat(btn.dataset.offset);
        subtitleOffset += offset;
        syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
        syncCuesToTextTrack();
        updateSubtitleDisplay();
    });
});

syncResetBtn.addEventListener('click', () => {
    subtitleOffset = 0;
    syncDisplay.textContent = '0.0s';
    syncCuesToTextTrack();
    updateSubtitleDisplay();
});

customSubBtn.addEventListener('click', () => customSubInput.click());
customSubInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const ext = file.name.split('.').pop().toLowerCase();
    const track = {
        type: 'external',
        label: `[로컬 파일] ${file.name}`,
        url: URL.createObjectURL(file),
        ext: ext,
        lang: ext
    };
    currentAvailableTracks.unshift(track);
    renderSubtitleDropdown(currentAvailableTracks, null);
    subSelect.value = '0';
    loadSelectedTrack(track);
});

if (fullscreenBtn) {
    fullscreenBtn.addEventListener('click', toggleFullscreen);
}
videoPlayer.addEventListener('dblclick', toggleFullscreen);

function closePlayer() {
    if (isFullscreen()) {
        exitFullscreenSafe();
    }
    videoPlayer.pause();
    videoPlayer.src = '';
    clearSubtitles();
    playerModal.classList.remove('active');
    hasCustomPosition = false;
    activeVideo = null;
}

closePlayerBtn.addEventListener('click', closePlayer);

document.addEventListener('keydown', (e) => {
    // Suppress player hotkeys when typing in search input or dropdowns (Item 20)
    if (e.target.matches('input, select, textarea') || e.target.isContentEditable) {
        if (e.key === 'Escape') e.target.blur();
        return;
    }
    if (e.key === 'Escape' && playerModal.classList.contains('active')) {
        if (isFullscreen()) {
            exitFullscreenSafe();
            e.preventDefault();
            e.stopPropagation();
            return;
        }
        closePlayer();
    }
    if (playerModal.classList.contains('active')) {
        if (e.key === 'f' || e.key === 'F') {
            toggleFullscreen();
        } else if (e.key === 'b' || e.key === 'B') {
            subBgEnabled = !subBgEnabled;
            localStorage.setItem('mycloud_sub_bg', subBgEnabled ? 'true' : 'false');
            applySubtitleStyle();
        } else if (e.key === '+' || e.key === '=') {
            updateSubtitleScale(subScale + 0.15);
        } else if (e.key === '-' || e.key === '_') {
            updateSubtitleScale(subScale - 0.15);
        } else if (e.key === '[') {
            subtitleOffset -= 0.5;
            syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
            syncCuesToTextTrack();
            updateSubtitleDisplay();
        } else if (e.key === ']') {
            subtitleOffset += 0.5;
            syncDisplay.textContent = (subtitleOffset >= 0 ? '+' : '') + subtitleOffset.toFixed(1) + 's';
            syncCuesToTextTrack();
            updateSubtitleDisplay();
        } else if (e.shiftKey && (e.key === 'N' || e.key === 'n')) {
            playNextVideo();
        } else if (e.shiftKey && (e.key === 'P' || e.key === 'p')) {
            playPrevVideo();
        }
    }
});

if (directLinkBtn) {
    directLinkBtn.addEventListener('click', () => {
        if (!activeVideo) return;
        const fullUrl = window.location.origin + activeVideo.url;
        navigator.clipboard.writeText(fullUrl).then(() => {
            showToast('동영상 주소가 클립보드에 복사되었습니다!');
        });
    });
}

let searchDebounceTimer = null;
searchInput.addEventListener('input', () => {
    const query = searchInput.value.toLowerCase().trim();
    clearSearchBtn.style.display = query ? 'block' : 'none';
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        applySortAndRender();
    }, 150); // 150ms debounce for smooth typing (Item 21)
});

clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    applySortAndRender();
});

refreshBtn.addEventListener('click', () => loadData(currentDir, currentMode));

function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

window.addEventListener('resize', () => {
    if (!playerModal.classList.contains('active')) return;
    if (hasCustomPosition) {
        const rect = modalDialog.getBoundingClientRect();
        const maxLeft = Math.max(10, window.innerWidth - modalDialog.offsetWidth - 10);
        const maxTop = Math.max(10, window.innerHeight - modalDialog.offsetHeight - 10);
        if (rect.left > maxLeft || rect.top > maxTop || rect.left < 10 || rect.top < 10) {
            modalDialog.style.left = `${Math.max(10, Math.min(rect.left, maxLeft))}px`;
            modalDialog.style.top = `${Math.max(10, Math.min(rect.top, maxTop))}px`;
        }
    } else {
        centerModalDialog();
    }
});

document.addEventListener('DOMContentLoaded', () => {
    applySubtitleStyle();
    setLayoutMode(currentLayout);
    loadData('', 'folder');
});
"""


def get_file_content(local_filename, default_content):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidate_paths = [
        os.path.join(cur_dir, "webplayer", local_filename),
        os.path.join(cur_dir, "apache", local_filename),
        os.path.join(cur_dir, local_filename),
        os.path.join(os.path.dirname(cur_dir), "webplayer", local_filename),
        os.path.join(os.path.dirname(cur_dir), "apache", local_filename),
        os.path.join(os.path.dirname(cur_dir), local_filename),
    ]
    for path in candidate_paths:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                rel = os.path.relpath(path, cur_dir)
                print(f"    (Deploying from local file: {rel})")
                return f.read()
    return default_content.encode('utf-8')

def main():
    print("[1] Connecting to WD My Cloud...")
    client = get_ssh_client()
    sftp = client.open_sftp()
    
    try:
        print("[2] Cleaning up old background extractor processes & disk cache...")
        client.exec_command('killall -9 avconv python 2>/dev/null; rm -rf /shares/Public/webplayer/cache/subtitles /shares/Public/webplayer/extract_subtitles.py /shares/Public/webplayer/extract.log /tmp/tmp_sub_* /tmp/test_* /tmp/webplayer_sub_ram/*')
        
        print("[3] Installing Apache webplayer configuration...")
        with sftp.open('/etc/apache2/conf.d/webplayer.conf', 'wb') as f:
            f.write(get_file_content('apache_webplayer.conf', APACHE_CONF))
            
        print("[4] Testing Apache configuration...")
        _, stdout, stderr = client.exec_command('. /etc/apache2/envvars && apache2 -t')
        chk = stdout.read().decode() + stderr.read().decode()
        print(f"Apache test: {chk.strip()}")
        
        print("[5] Writing stream_sub.py (Zero-disk demuxer)...")
        with sftp.open('/shares/Public/webplayer/stream_sub.py', 'wb') as f:
            f.write(get_file_content('stream_sub.py', STREAM_SUB_PY))
            
        print("[6] Writing api.php...")
        with sftp.open('/shares/Public/webplayer/api.php', 'wb') as f:
            f.write(get_file_content('api.php', API_PHP))
            
        print("[7] Writing index.html...")
        # Bump the ?v= cache-busting suffix on every deploy - a static version
        # string here means a phone/tablet that already cached style.css or
        # app.js can keep serving the stale file after a normal refresh, even
        # though the server has the fix. This was silently biting the Android
        # tablet fixes earlier - always deploy a fresh value instead of
        # relying on remembering to bump it by hand.
        cache_version = time.strftime('%Y%m%d%H%M%S')
        index_content = get_file_content('index.html', INDEX_HTML)
        # Match up to the closing quote (not just \d+) so a stray suffix left
        # over from a hand-edited version string (e.g. "?v=20260911_v3") gets
        # replaced outright instead of prepended-to.
        index_content = re.sub(br'\?v=[^"\']*', b'?v=' + cache_version.encode('ascii'), index_content)
        with sftp.open('/shares/Public/webplayer/index.html', 'wb') as f:
            f.write(index_content)
            
        print("[8] Writing style.css...")
        with sftp.open('/shares/Public/webplayer/style.css', 'wb') as f:
            f.write(get_file_content('style.css', STYLE_CSS))
            
        print("[9] Writing app.js...")
        with sftp.open('/shares/Public/webplayer/app.js', 'wb') as f:
            f.write(get_file_content('app.js', APP_JS))
            
        print("[10] Setting permissions for Windows Explorer editability...")
        nas_owner = os.environ.get('NAS_OWNER', 'root')
        nas_group = os.environ.get('NAS_GROUP', 'share')
        _, stdout, _ = client.exec_command(f'chmod -R 777 /shares/Public/webplayer; chown -R {nas_owner}:{nas_group} /shares/Public/webplayer')
        stdout.read()
        
        print("[11] Restarting Apache...")
        _, stdout, _ = client.exec_command('service apache2 restart')
        stdout.read()
        
        print("\nDeployment completed successfully! Zero disk cache active.")
    finally:
        sftp.close()
        client.close()

if __name__ == '__main__':
    main()
