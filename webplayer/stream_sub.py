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
        
    # Sort: Korean CONTENT first (detect actual hangul text), then kor-tagged, then others
    # This handles Netflix/Rarbg multi-lang MKVs where language tags are wrong (e.g. kor tag = Japanese text)
    import re as _re

    # Pre-load Cues section ONCE (used by has_hangul_content for all kor tracks)
    _seg_start = seg_data_start
    _cues_data = None
    if cues_offset is not None:
        try:
            fc = open(video_path, 'rb')
            fc.seek(_seg_start + cues_offset)
            ch = fc.read(12)
            cid2, cl2 = read_id(ch, 0)
            csz2, csl2 = read_vint(ch, cl2)
            fc.seek(_seg_start + cues_offset + cl2 + csl2)
            _cues_data = fc.read(csz2)
            fc.close()
        except Exception:
            _cues_data = None

    def has_hangul_content(sub_entry, seg_start=_seg_start, cues_data=_cues_data):
        """Sample the first dialogue line's actual text (properly parsed out of its
        Block/BlockGroup, not raw bytes) and check for Hangul (U+AC00-U+D7A3).
        Pure in-process seek+read (no subprocess spawn) - a full Python interpreter
        cold-start per candidate track was the real cost on this 650MHz CPU, since a
        multi-language MKV can have several kor-tagged tracks to disambiguate."""
        if cues_data is None:
            return False
        try:
            tnum2 = sub_entry.get('track_number')
            if tnum2 is None:
                return False
            if tnum2 < 128:
                tsig = b'\xf7\x81' + chr(tnum2)
            else:
                tsig = b'\xf7\x82' + chr(tnum2 >> 8) + chr(tnum2 & 0xFF)
            idx2 = cues_data.find(tsig)
            if idx2 == -1:
                return False
            b7 = cues_data.rfind(b'\xb7', max(0, idx2 - 15), idx2)
            if b7 == -1:
                return False
            _, el2 = read_id(cues_data, b7)
            esz2, esl2 = read_vint(cues_data, b7 + el2)
            if esz2 is None:
                return False
            tp2 = b7 + el2 + esl2
            tp2_end = tp2 + esz2
            cpos2 = None
            rpos2 = 0
            while tp2 < tp2_end:
                tid2, il2 = read_id(cues_data, tp2)
                if tid2 is None: break
                tsz2, tsl2 = read_vint(cues_data, tp2 + il2)
                if tsz2 is None: break
                vp2 = tp2 + il2 + tsl2
                if tid2 == 0xF1:  # CueClusterPosition
                    v2 = 0
                    for i in range(tsz2): v2 = (v2 << 8) | ord(cues_data[vp2 + i])
                    cpos2 = v2
                elif tid2 == 0xF0:  # CueRelativePosition
                    v2 = 0
                    for i in range(tsz2): v2 = (v2 << 8) | ord(cues_data[vp2 + i])
                    rpos2 = v2
                tp2 = vp2 + tsz2
            if cpos2 is None:
                return False

            fh = open(video_path, 'rb')
            try:
                # Cluster header (ID + size vint) sits before its data - skip past it,
                # same as the main streaming loop, instead of reading straight from
                # seg_start+cpos+rpos (that offset lands inside the header, not the
                # Block, which was the original bug: garbled bytes -> Hangul missed).
                abs_cluster = seg_start + cpos2
                fh.seek(abs_cluster + 4)
                b0 = ord(fh.read(1))
                vlen = 1
                for l in range(1, 9):
                    if b0 & (0x80 >> (l - 1)):
                        vlen = l
                        break
                cluster_data_start = abs_cluster + 4 + vlen
                fh.seek(cluster_data_start + rpos2)
                block_hdr = fh.read(1024)
            finally:
                fh.close()

            txt = None
            eid, el = read_id(block_hdr, 0)
            if eid == 0xA0:  # BlockGroup
                esz, esl = read_vint(block_hdr, el)
                if esz is not None:
                    bg_data = block_hdr[el + esl: el + esl + esz]
                    bp = 0
                    while bp < len(bg_data):
                        bid, bl = read_id(bg_data, bp)
                        if bid is None: break
                        bsz, bsl = read_vint(bg_data, bp + bl)
                        if bsz is None: break
                        if bid == 0xA1:  # Block
                            block_payload = bg_data[bp + bl + bsl: bp + bl + bsl + bsz]
                            tn, tlen = read_vint(block_payload, 0)
                            if tn == tnum2:
                                txt = block_payload[tlen + 3:]
                            break
                        bp += bl + bsl + bsz
            elif eid == 0xA1 or eid == 0xA3:  # Block or SimpleBlock
                esz, esl = read_vint(block_hdr, el)
                if esz is not None:
                    block_payload = block_hdr[el + esl: el + esl + esz]
                    tn, tlen = read_vint(block_payload, 0)
                    if tn == tnum2:
                        txt = block_payload[tlen + 3:]

            if not txt:
                return False
            sample = txt[:500].decode('utf-8', errors='replace')
            return bool(_re.search(u'[\uAC00-\uD7A3]', sample))
        except Exception:
            return False

    def sub_sort_key(s):
        lang = s['lang'].lower() if isinstance(s['lang'], str) else s['lang'].lower()
        is_forced = 1 if s['is_forced'] else 0
        # Priority 0: kor-tagged AND actually has hangul text (real Korean content)
        # Priority 1: kor-tagged but no hangul detected (wrong tag, e.g. Japanese text)
        # Priority 2: all other languages
        if lang in ('kor', 'ko', 'korean'):
            real_kor = 0 if has_hangul_content(s) else 1
            return (real_kor, is_forced, s['stream_id'])
        return (2, is_forced, s['stream_id'])

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
            # Match by position only - the frontend always sends the probe's
            # 'stream_id' (a running index over subtitle tracks), never the raw
            # Matroska TrackNumber. Also matching on tnum == target_stream_idx
            # caused the wrong track to be picked whenever some track's actual
            # TrackNumber happened to equal the requested stream_id (easy to hit
            # on files with dozens of tracks, e.g. multi-language releases).
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
            # Backward byte-scan for the CueTime (0xB3) tag - occasionally this
            # matches a stray 0xB3 byte that isn't really the tag (coincidental
            # data, not a real EBML boundary). The bounds check below makes that
            # a no-op (ctime stays 0) instead of reading past cues_data and
            # crashing the whole process with an unhandled IndexError.
            t_idx = cues_data.rfind(b'\xb3', max(0, b7_idx - 30), b7_idx)
            ctime = 0
            if t_idx != -1:
                _, tl = read_id(cues_data, t_idx)
                tsz, tsl = read_vint(cues_data, t_idx + tl)
                if tsz is not None and t_idx + tl + tsl + tsz <= len(cues_data):
                    v = 0
                    for i in range(tsz): v = (v << 8) | ord(cues_data[t_idx + tl + tsl + i])
                    ctime = v
            cues.append((ctime, dur, cpos, rpos))
            
    if not cues:
        f.close()
        fallback_avconv_stream(video_path, stream_id)
        return

    # Guarantee chronological + physically-ascending disk order. In practice the
    # Cues table is already written this way (verified: 0 backward jumps across
    # real sample files), so this is a cheap safety net rather than the fix for
    # a measured problem - but it also means the HDD head never has to seek
    # backward if some file ever isn't perfectly ordered.
    cues.sort(key=lambda c: c[0])

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

        # A dialogue block (header + text) is essentially always well under 1KB;
        # 2048 keeps a wide safety margin for long ASS override-tag lines while
        # still halving the bytes pulled off the platter vs the old 4096 read.
        block_hdr = f.read(2048)
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
