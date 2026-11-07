#!/usr/bin/env python
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

_orig_ord = ord
def ord(x):
    return x if isinstance(x, int) else _orig_ord(x)

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

def ms_to_ass(ms):
    if ms < 0: ms = 0
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms_part = divmod(rem, 1000)
    cs = ms_part // 10
    return "%d:%02d:%02d.%02d" % (h, m, s, cs)

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
    if sh_idx == -1:
        tr_idx = hdr.find(b'\x16\x54\xae\x6b', seg_data_start)
        tracks_off = (tr_idx - seg_data_start) if tr_idx != -1 else None
        return seg_data_start, tracks_off, None
    
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

    if tracks_offset is None:
        tr_idx = hdr.find(b'\x16\x54\xae\x6b', seg_data_start)
        if tr_idx != -1:
            tracks_offset = tr_idx - seg_data_start
        
    return seg_data_start, tracks_offset, cues_offset

def probe_subtitles(video_path):
    try:
        f = open(video_path, 'rb')
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
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
            tdef = 0
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
    print(json.dumps({'success': True, 'subtitles': subs}))

def fallback_avconv_probe(video_path):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/usr/local/wdmcserver/lib'
    cmd = ['/usr/local/wdmcserver/bin/avconv', '-probesize', '32768', '-analyzeduration', '0', '-i', video_path]
    try:
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, stderr_data = p.communicate()
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))
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
    print(json.dumps({'success': True, 'subtitles': subs}))

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
            if is_sub and cur_stream == target_stream_idx:
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
    
    # Fast search for target track using top-level CuePoint (0xBB) boundaries
    # combined with cues_data.find(track_sig) skip-ahead so we never misidentify
    # a 0xB3/0xB7 byte inside an offset integer and never fail when a CuePoint
    # has many CueTrackPositions (> 30 bytes away from CueTime).
    if target_track_num < 128:
        track_sig = b'\xf7\x81' + struct.pack('>B', target_track_num)
    else:
        track_sig = b'\xf7\x82' + struct.pack('>H', target_track_num)
        
    cues = []
    cp = 0
    cues_len = len(cues_data)
    next_sig_idx = cues_data.find(track_sig, 0)
    while cp < cues_len and next_sig_idx != -1:
        cp_id, cp_id_len = read_id(cues_data, cp)
        if cp_id is None:
            break
        cp_sz, cp_sz_len = read_vint(cues_data, cp + cp_id_len)
        if cp_sz is None:
            break
        cp_body = cp + cp_id_len + cp_sz_len
        cp_end = cp_body + cp_sz
        if cp_id != 0xBB or cp_end <= next_sig_idx:
            cp = cp_end
            continue
        # This CuePoint (0xBB) contains track_sig; parse its children cleanly
        ctime = 0
        matched_positions = []
        ip = cp_body
        while ip < cp_end:
            chid, chid_len = read_id(cues_data, ip)
            if chid is None:
                break
            chsz, chsz_len = read_vint(cues_data, ip + chid_len)
            if chsz is None:
                break
            ch_body = ip + chid_len + chsz_len
            ch_end = ch_body + chsz
            if chid == 0xB3: # CueTime
                v = 0
                for i in range(chsz):
                    v = (v << 8) | ord(cues_data[ch_body + i])
                ctime = v
            elif chid == 0xB7: # CueTrackPositions
                tp = ch_body
                t_track = None
                cpos = None
                rpos = 0
                dur = 0
                while tp < ch_end:
                    tag_id, id_len = read_id(cues_data, tp)
                    if tag_id is None:
                        break
                    tag_sz, sz_len = read_vint(cues_data, tp + id_len)
                    if tag_sz is None:
                        break
                    vpos = tp + id_len + sz_len
                    if tag_id == 0xF7: # CueTrack
                        v = 0
                        for i in range(tag_sz):
                            v = (v << 8) | ord(cues_data[vpos + i])
                        t_track = v
                    elif tag_id == 0xF1: # CueClusterPosition
                        v = 0
                        for i in range(tag_sz):
                            v = (v << 8) | ord(cues_data[vpos + i])
                        cpos = v
                    elif tag_id == 0xF0: # CueRelativePosition
                        v = 0
                        for i in range(tag_sz):
                            v = (v << 8) | ord(cues_data[vpos + i])
                        rpos = v
                    elif tag_id == 0xB2: # CueDuration
                        v = 0
                        for i in range(tag_sz):
                            v = (v << 8) | ord(cues_data[vpos + i])
                        dur = v
                    tp = vpos + tag_sz
                if t_track == target_track_num and cpos is not None:
                    matched_positions.append((cpos, rpos, dur))
            ip = ch_end
        for cpos, rpos, dur in matched_positions:
            cues.append((ctime, dur, cpos, rpos))
        cp = cp_end
        if cp > next_sig_idx:
            next_sig_idx = cues_data.find(track_sig, cp)
            
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
            block_hdr = f.read(1024)
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
                if cue_idx == 1 or (cue_idx % 40) == 0:
                    sys.stdout.flush()
                cue_idx += 1
            except IOError:
                break
                
    try:
        sys.stdout.flush()
    except IOError:
        pass
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
