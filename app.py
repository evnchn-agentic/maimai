#!/usr/bin/env python3
"""
maimai-claude-code Dashboard — NiceGUI frontend.
Focused on Umiyuri pattern detection visualization.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nicegui import app, ui
from simai_parser import parse_maidata, parse_chart_string, Note
from pattern_discovery import (
    window_notes, extract_features, detect_pattern_candidates
)
from umiyuri_detector import detect_umiyuri, umiyuri_score
from paika_detector import detect_paika, paika_score
from slide_reading_detector import detect_slide_reading, slide_reading_score
from collections import Counter, defaultdict
import math

# Inline 一筆畫 and 魔法陣 detectors
def detect_hitofude(notes, min_chain=3):
    slides = sorted([n for n in notes if n.note_type == 'slide' and n.slide_duration_ms > 0],
                     key=lambda n: n.time_ms)
    if len(slides) < 2: return []
    detections = []; i = 0
    while i < len(slides) - 1:
        chain = [slides[i]]; j = i + 1
        while j < len(slides):
            if chain[-1].slide_end == slides[j].position and slides[j].time_ms - chain[-1].time_ms < 2000:
                chain.append(slides[j]); j += 1
            else: break
        if len(chain) >= min_chain:
            detections.append({'start_s': chain[0].time_ms/1000, 'end_s': chain[-1].time_ms/1000,
                              'duration_s': (chain[-1].time_ms - chain[0].time_ms)/1000, 'chain': len(chain)})
        i = j if j > i else i + 1
    return detections

_POS_A = {i+1: math.radians(45*i) for i in range(8)}
def _pxy(p): a=_POS_A[p]; return (math.cos(a), math.sin(a))
def _seg_cross(p1,p2,p3,p4):
    def c2(a,b): return a[0]*b[1]-a[1]*b[0]
    d1=(p2[0]-p1[0],p2[1]-p1[1]); d2=(p4[0]-p3[0],p4[1]-p3[1]); dn=c2(d1,d2)
    if abs(dn)<1e-10: return False
    t=c2((p3[0]-p1[0],p3[1]-p1[1]),d2)/dn; u=c2((p3[0]-p1[0],p3[1]-p1[1]),d1)/dn
    return 0.05<t<0.95 and 0.05<u<0.95

def detect_mahoujin(notes, min_slides=3):
    slides = sorted([n for n in notes if n.note_type == 'slide' and n.slide_duration_ms > 0
                     and n.slide_shape == '-' and (n.slide_end - n.position) % 8 == 4],
                    key=lambda n: n.time_ms)
    if len(slides) < min_slides: return []
    beat_ms = 60000.0 / notes[0].bpm if notes else 500
    detections = []; i = 0
    while i < len(slides) - 2:
        chain = [slides[i]]; keys = [f'{slides[i].position}-{slides[i].slide_end}']
        j = i + 1
        while j < len(slides):
            s = slides[j]; gap = s.time_ms - chain[-1].time_ms
            if gap > beat_ms * 1.5: break
            if gap < beat_ms * 0.5: j += 1; continue
            nk = f'{s.position}-{s.slide_end}'
            if nk == keys[-1]: j += 1; continue
            p1,p2 = _pxy(s.position),_pxy(s.slide_end); ok = False
            for k in range(max(0,len(chain)-3),len(chain)):
                if chain[k].time_ms > s.time_ms - beat_ms*2.5:
                    if _seg_cross(p1,p2,_pxy(chain[k].position),_pxy(chain[k].slide_end)): ok=True; break
            if ok: chain.append(s); keys.append(nk); j+=1
            else: break
        if len(chain) >= min_slides and len(set(keys)) >= 3:
            starts = [c.position for c in chain]
            if len(set(starts)) / len(chain) >= 0.7:
                detections.append({'start_s': chain[0].time_ms/1000, 'end_s': chain[-1].time_ms/1000,
                                  'duration_s': (chain[-1].time_ms-chain[0].time_ms)/1000, 'chain': len(chain)})
        i += 1
    merged = []
    for d in detections:
        if merged and d['start_s'] - merged[-1]['end_s'] < 2:
            if d['chain'] > merged[-1]['chain']: merged[-1] = d
        else: merged.append(d)
    return merged

    tg = defaultdict(list)
    for n in notes:
        tg[round(n.time_ms / 10) * 10].append(n)
    ds_times = []
    for t in sorted(tg.keys()):
        g = tg[t]; slides = [n for n in g if n.note_type == 'slide']; taps = [n for n in g if n.note_type in ('tap', 'break')]
        if slides and taps:
            for s in slides:
                for tap in taps:
                    dist = min(abs(tap.position - s.position), 8 - abs(tap.position - s.position))
                    if dist == 1: ds_times.append(t); break
                else: continue
                break
    if not ds_times: return []
    detections = []; i = 0
    while i < len(ds_times):
        chain = [ds_times[i]]; j = i + 1
        while j < len(ds_times):
            if ds_times[j] - chain[-1] < 1500: chain.append(ds_times[j]); j += 1
            else: break
        if len(chain) >= min_consecutive:
            detections.append({'start_s': chain[0]/1000, 'end_s': chain[-1]/1000,
                              'duration_s': (chain[-1]-chain[0])/1000, 'count': len(chain)})
        i = j if j > i else i + 1
    return detections


def nav_header():
    """Shared navigation header."""
    with ui.header().classes('bg-blue-900'):
        ui.label('maimai pattern detector').classes('text-xl font-bold')
        ui.link('Detector', '/').classes('text-white ml-4')
        ui.link('Umiyuri', '/leaderboard').classes('text-white ml-4')
        ui.link('轉圈', '/rotation').classes('text-white ml-4')
        ui.link('縦連', '/jacks').classes('text-white ml-4')
        ui.link('トリル', '/trills').classes('text-white ml-4')
        ui.link('乱打', '/randaa').classes('text-white ml-4')
        ui.link('一筆畫', '/hitofude').classes('text-white ml-4')
        ui.link('魔法陣', '/mahoujin').classes('text-white ml-4')

BASE = os.path.dirname(os.path.abspath(__file__))


def load_chart(filepath, difficulty=5):
    """Load and parse a chart file."""
    data = parse_maidata(filepath)
    meta = data['metadata']
    if difficulty not in data['charts']:
        difficulty = max(data['charts'].keys())
    notes = parse_chart_string(data['charts'][difficulty], meta.bpm)
    level = data.get(f'lv_{difficulty}', '?')
    return meta, notes, level, difficulty


def analyze_chart_patterns(notes, window_ms=2000.0, step_ms=500.0):
    """Run pattern analysis on a chart, return per-window results."""
    windows = window_notes(notes, window_ms=window_ms, step_ms=step_ms)
    results = []
    for w in windows:
        feats = extract_features(w)
        if feats:
            feats['_time'] = w.start_ms
            feats['_end'] = w.end_ms
            feats['_note_count'] = len(w.notes)
            results.append(feats)
    return results


def get_pattern_timeline(results):
    """Build a timeline of detected patterns."""
    pattern_defs = {
        '拍滑': lambda r: r.get('tap_slide_simultaneous', 0) > 0.3 and r.get('slide_count', 0) >= 3,
        'stream': lambda r: (r.get('note_density', 0) > 6 and r.get('directional_bias', 0) > 0.5
                              and r.get('rhythm_regularity', 0) > 0.7 and r.get('ratio_slide', 0) < 0.1),
        'jacks': lambda r: r.get('jack_ratio', 0) > 0.3,
        'cross-hand': lambda r: r.get('cross_hand_ratio', 0) > 0.6 and r.get('note_density', 0) > 6,
        '散打': lambda r: r.get('avg_movement', 0) > 2.0 and r.get('note_density', 0) > 4 and r.get('directional_bias', 0) < 0.5,
    }

    timeline = []
    for r in results:
        t = r['_time'] / 1000.0
        detected = [name for name, check in pattern_defs.items() if check(r)]
        timeline.append({
            'time': t,
            'patterns': detected,
            'density': r.get('note_density', 0),
            'slide_ratio': r.get('ratio_slide', 0),
            'each_ratio': r.get('each_ratio', 0),
            'cross_hand': r.get('cross_hand_ratio', 0),
            'tap_slide_simul': r.get('tap_slide_simultaneous', 0),
            'movement': r.get('avg_movement', 0),
        })
    return timeline


def find_chart_files():
    """Find all available chart files. Returns dict of title -> path."""
    charts = {}
    for root, dirs, files in os.walk(os.path.join(BASE, 'Maichart-Converts-1.60_1.0.9.0')):
        for f in files:
            if f == 'maidata.txt':
                path = os.path.join(root, f)
                try:
                    data = parse_maidata(path)
                    title = data['metadata'].title
                    charts[title] = path
                except:
                    pass
    for root, dirs, files in os.walk(os.path.join(BASE, 'audio-data')):
        for f in files:
            if f == 'maidata.txt':
                path = os.path.join(root, f)
                try:
                    data = parse_maidata(path)
                    title = data['metadata'].title
                    if title not in charts:
                        charts[title] = path
                except:
                    pass
    return charts


# Build song index at startup
print("Building song index...")
SONG_INDEX = find_chart_files()
print(f"Indexed {len(SONG_INDEX)} songs")


# Preload Umiyuri for fast startup
UMIYURI_PATH = os.path.join(BASE, 'Maichart-Converts-1.60_1.0.9.0',
                             'niconicoボーカロイド', '417_ウミユリカイテイタン', 'maidata.txt')


# ─── UI ───

@ui.page('/')
def main_page():
    ui.dark_mode().enable()

    nav_header()

    # State
    state = {'chart_path': UMIYURI_PATH, 'difficulty': 5}

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Chart Pattern Detector').classes('text-2xl font-bold mb-2')
        ui.label('Select a song and analyze its chart patterns — Umiyuri, 拍滑, slides, streams, and more.').classes('text-gray-400 mb-4')

        # Chart selector — searchable
        song_options = {title: title for title in sorted(SONG_INDEX.keys())}
        # Find Umiyuri's title key
        default_song = next((t for t in SONG_INDEX if 'ウミユリ' in t), list(SONG_INDEX.keys())[0])

        with ui.row().classes('w-full items-end gap-4 mb-4'):
            song_select = ui.select(
                song_options, value=default_song, label='Song',
                with_input=True,
            ).classes('flex-grow').props('use-input input-debounce=300')
            diff_select = ui.select(
                {2: 'Basic', 3: 'Advanced', 4: 'Expert', 5: 'Master', 6: 'Re:Master'},
                value=5, label='Difficulty'
            ).classes('w-40')
            cycles_select = ui.select(
                {2: '2+ cycles (R&D)', 3: '3+ cycles', 4: '4+ cycles (strict)'},
                value=4, label='Min cycles'
            ).classes('w-48')
            analyze_btn = ui.button('Analyze', icon='search')

        # Results container
        results_container = ui.column().classes('w-full')

        def run_analysis():
            results_container.clear()
            title = song_select.value
            path = SONG_INDEX.get(title)
            diff = diff_select.value

            if not path or not os.path.exists(path):
                with results_container:
                    ui.label(f'Song not found: {title}').classes('text-red-400')
                return

            try:
                meta, notes, level, actual_diff = load_chart(path, diff)
            except Exception as e:
                with results_container:
                    ui.label(f'Parse error: {e}').classes('text-red-400')
                return

            results = analyze_chart_patterns(notes)
            timeline = get_pattern_timeline(results)

            with results_container:
                # Compact header: song info + note types + detector scores all in one row
                type_counts = Counter(n.note_type for n in notes)
                with ui.row().classes('w-full items-center gap-4 mb-2 flex-wrap'):
                    ui.label(f'{meta.title}').classes('text-lg font-bold')
                    ui.label(f'{meta.artist} | BPM {meta.bpm} | Lv.{level} | {len(notes)} notes').classes('text-sm text-gray-400')
                    for ntype, count in type_counts.most_common():
                        ui.badge(f'{count} {ntype}', color='blue-grey').classes('text-xs')

                # Precompute everything needed for timeline
                pattern_colors = {
                    '拍滑': '#ef4444',
                    'stream': '#3b82f6',
                    'jacks': '#f59e0b',
                    'cross-hand': '#8b5cf6',
                    '散打': '#ec4899',
                }
                pattern_names = list(pattern_colors.keys())
                series_data = {p: [] for p in pattern_names}
                for t in timeline:
                    time_s = t['time']
                    for p in pattern_names:
                        series_data[p].append([time_s, 1 if p in t['patterns'] else 0])
                density_data = [[t['time'], t['density']] for t in timeline]
                song_end_s = max(n.time_ms for n in notes) / 1000.0 if notes else 0

                # Combo mapping
                sorted_notes_for_combo = sorted(notes, key=lambda n: (n.time_ms, n.position))
                combo_map = []
                combo_num = 0
                for n in sorted_notes_for_combo:
                    combo_num += 1
                    combo_map.append((combo_num, n.time_ms))
                    if n.note_type == 'slide':
                        combo_num += 1
                        combo_map.append((combo_num, n.slide_end_ms))
                max_combo = combo_num

                # Run all detectors
                umiyuri_detections = detect_umiyuri(notes, min_cycles=cycles_select.value)
                u_score = umiyuri_score(notes)
                paika_dets = detect_paika(notes)
                p_score = paika_score(notes)
                sr_dets = detect_slide_reading(notes)
                sr_score = slide_reading_score(notes)
                hitofude_dets = detect_hitofude(notes)
                mahoujin_dets = detect_mahoujin(notes)

                # Build mark areas for all detectors
                umiyuri_mark_areas = []
                for d in umiyuri_detections:
                    umiyuri_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(34, 197, 94, 0.15)'}},
                        {'xAxis': d['end_s']},
                    ])
                paika_mark_areas = []
                for d in paika_dets:
                    paika_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(6, 182, 212, 0.1)'}},
                        {'xAxis': d['end_s']},
                    ])
                sr_mark_areas = []
                for d in sr_dets:
                    sr_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(251, 146, 60, 0.1)'}},
                        {'xAxis': d['end_s']},
                    ])
                hitofude_mark_areas = []
                for d in hitofude_dets:
                    hitofude_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(168, 85, 247, 0.15)'}},
                        {'xAxis': d['end_s']},
                    ])
                mahoujin_mark_areas = []
                for d in mahoujin_dets:
                    mahoujin_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(236, 72, 153, 0.15)'}},
                        {'xAxis': d['end_s']},
                    ])

                # Multi-timeline: each detector gets its own row
                # Shared x-axis, stacked grids
                x_max = round(song_end_s + 1)

                def make_timeline_bar(mark_areas, y_val=0.5):
                    """Convert mark areas into bar segments for a single-row timeline."""
                    bars = []
                    for ma in mark_areas:
                        start = ma[0]['xAxis']
                        end = ma[1]['xAxis']
                        bars.append([start, y_val])
                        bars.append([end, y_val])
                    return bars

                # Build per-window pattern mark areas from the timeline data
                pattern_mark_builders = {
                    '拍滑': ('#ef4444', []),
                    'stream': ('#3b82f6', []),
                    'jacks': ('#f59e0b', []),
                    'cross-hand': ('#8b5cf6', []),
                    '散打': ('#ec4899', []),
                }
                # Group consecutive windows with same pattern into mark areas
                for pname in pattern_mark_builders:
                    in_section = False
                    start_t = 0
                    for t in timeline:
                        if pname in t['patterns']:
                            if not in_section:
                                start_t = t['time']
                                in_section = True
                        else:
                            if in_section:
                                pattern_mark_builders[pname][1].append([
                                    {'xAxis': start_t}, {'xAxis': t['time']}
                                ])
                                in_section = False
                    if in_section and timeline:
                        pattern_mark_builders[pname][1].append([
                            {'xAxis': start_t}, {'xAxis': timeline[-1]['time']}
                        ])

                detector_rows = [
                    ('Density', density_data, None, '#ffffff44', 'line'),
                    ('ウミユリ', None, umiyuri_mark_areas, '#22c55e', 'area'),
                    ('拍滑 (simul)', None, paika_mark_areas, '#06b6d4', 'area'),
                    ('Slide Reading', None, sr_mark_areas, '#fb923c', 'area'),
                    ('一筆畫', None, hitofude_mark_areas, '#a855f7', 'area'),
                    ('魔法陣', None, mahoujin_mark_areas, '#ec4899', 'area'),
                ]
                # Add coarse pattern rows that have detections
                for pname, (color, marks) in pattern_mark_builders.items():
                    if marks:
                        detector_rows.append((pname, None, marks, color, 'area'))

                # Filter to rows that have data
                active_rows = [(name, data, marks, color, typ) for name, data, marks, color, typ in detector_rows
                               if data or marks]
                n_rows = len(active_rows)

                # Build multi-grid echart
                grids = []
                x_axes = []
                y_axes = []
                series = []

                row_height = 60
                density_height = 120
                top_margin = 30

                for idx, (name, line_data, marks, color, typ) in enumerate(active_rows):
                    is_density = typ == 'line'
                    h = density_height if is_density else row_height
                    t = top_margin + sum(density_height if active_rows[j][4] == 'line' else row_height for j in range(idx)) + idx * 10

                    grids.append({
                        'top': t, 'height': h, 'left': 80, 'right': 20,
                    })
                    x_axes.append({
                        'type': 'value', 'min': 0, 'max': x_max,
                        'gridIndex': idx,
                        'axisLabel': {'show': idx == n_rows - 1, 'color': '#999'},
                        'axisLine': {'show': False},
                        'axisTick': {'show': False},
                    })

                    if is_density:
                        y_axes.append({
                            'type': 'value', 'gridIndex': idx,
                            'name': name, 'nameTextStyle': {'color': color, 'fontSize': 11},
                            'axisLabel': {'color': '#999', 'fontSize': 9},
                        })
                        series.append({
                            'name': name, 'type': 'line',
                            'xAxisIndex': idx, 'yAxisIndex': idx,
                            'data': line_data,
                            'lineStyle': {'color': color, 'width': 1},
                            'itemStyle': {'color': color},
                            'symbol': 'none',
                            'areaStyle': {'color': color, 'opacity': 0.05},
                        })
                    else:
                        y_axes.append({
                            'type': 'value', 'min': 0, 'max': 1, 'gridIndex': idx,
                            'name': name, 'nameTextStyle': {'color': color, 'fontSize': 11},
                            'axisLabel': {'show': False},
                            'splitLine': {'show': False},
                        })
                        # Render mark areas as a series of rectangles
                        if marks:
                            for ma in marks:
                                start = ma[0]['xAxis']
                                end = ma[1]['xAxis']
                                series.append({
                                    'type': 'bar',
                                    'xAxisIndex': idx, 'yAxisIndex': idx,
                                    'data': [[start, 1]],
                                    'barWidth': f'{max(1, (end - start) / x_max * 100)}%',
                                    'itemStyle': {'color': color, 'opacity': 0.6},
                                    'showBackground': False,
                                    'silent': True,
                                })
                            # Simpler approach: use markArea on a dummy line
                            series.append({
                                'name': name, 'type': 'line',
                                'xAxisIndex': idx, 'yAxisIndex': idx,
                                'data': [[0, 0.5], [x_max, 0.5]],
                                'lineStyle': {'color': 'transparent'},
                                'symbol': 'none',
                                'markArea': {
                                    'silent': True,
                                    'data': marks,
                                    'itemStyle': {'color': color, 'opacity': 0.4},
                                    'label': {'show': False},
                                },
                            })

                total_height = top_margin + sum(density_height if r[4] == 'line' else row_height for r in active_rows) + n_rows * 10 + 40

                echart_options = {
                    'tooltip': {'trigger': 'axis'},
                    'axisPointer': {'link': [{'xAxisIndex': 'all'}]},
                    'grid': grids,
                    'xAxis': x_axes,
                    'yAxis': y_axes,
                    'series': series,
                }

                ui.echart(echart_options).style(f'width:100%;height:{total_height}px')

                # Detection summary below timeline — show all detectors that found something
                hitofude_total = sum(d['chain'] for d in hitofude_dets)
                mahoujin_total = sum(d['chain'] for d in mahoujin_dets)
                all_detections = [
                    ('Umiyuri', f'{u_score:.0%}', 'green-400', u_score > 0),
                    ('拍滑', f'{p_score:.0%}', 'cyan-400', p_score > 0),
                    ('Slide Reading', f'{sr_score:.0%}', 'orange-400', sr_score > 0),
                    ('一筆畫', f'{hitofude_total}ch', 'purple-400', hitofude_total > 0),
                    ('魔法陣', f'{mahoujin_total}ch', 'pink-400', mahoujin_total > 0),
                ]
                # Add coarse pattern detections
                all_patterns = defaultdict(int)
                for t in timeline:
                    for p in t['patterns']:
                        all_patterns[p] += 1
                coarse_colors = {
                    '拍滑': ('red-400', '#ef4444'),
                    'stream': ('blue-400', '#3b82f6'),
                    'jacks': ('yellow-400', '#f59e0b'),
                    'cross-hand': ('purple-400', '#8b5cf6'),
                    '散打': ('pink-400', '#ec4899'),
                }
                for pname, count in sorted(all_patterns.items(), key=lambda x: -x[1]):
                    if pname in coarse_colors:
                        pct = count / len(timeline) * 100 if timeline else 0
                        color = coarse_colors[pname][0]
                        all_detections.append((pname, f'{pct:.0f}%', color, pct > 0))

                all_detections.append(('Max Combo', str(max_combo), 'gray-400', True))

                with ui.row().classes('gap-3 mt-2 flex-wrap'):
                    for label, value, color, show in all_detections:
                        if show:
                            with ui.card().classes('p-2'):
                                ui.label(value).classes(f'text-xl font-bold text-{color}')
                                ui.label(label).classes('text-xs text-gray-400')

        analyze_btn.on_click(run_analysis)
        # Auto-run on load
        run_analysis()


@ui.page('/status')
def status_page():
    ui.dark_mode().enable()

    nav_header()

    with ui.column().classes('w-full max-w-4xl mx-auto p-4'):
        ui.label('Pipeline Status').classes('text-2xl font-bold mb-4')

        stages = [
            ('Chart Data', 'done', '1,717 maidata.txt files'),
            ('Audio Data', 'done', '1,184 track.mp3 files (6.1GB)'),
            ('Simai Parser', 'done', 'Parser + ASCII visualizer'),
            ('Pattern Discovery', 'done', '7 pattern types, 241K windows'),
            ('Score Analysis', 'done', '31 players, pattern-perf cross-analysis'),
            ('Beat Detection', 'in progress', 'librosa working, Umiyuri: 117.5 BPM detected (known: 120)'),
            ('Chart Gen v1', 'done', 'Procedural, 4 styles in review queue'),
            ('Chart Gen v2', 'pending', 'Data-driven from corpus'),
            ('Pattern Understanding', 'pending', 'Weight inspection / fuzzing'),
            ('Player Recommendations', 'pending', 'Rating grind / skill improvement'),
        ]

        for name, status, detail in stages:
            color = {'done': 'green', 'in progress': 'yellow', 'pending': 'gray'}[status]
            with ui.row().classes('items-center gap-3 mb-2'):
                ui.icon('check_circle' if status == 'done' else
                        'pending' if status == 'in progress' else 'radio_button_unchecked',
                        color=color).classes('text-xl')
                ui.label(name).classes('w-48 font-bold')
                ui.badge(status, color=color)
                ui.label(detail).classes('text-gray-400 text-sm')

        # Stats
        ui.label('Dataset Stats').classes('text-xl font-bold mt-8 mb-4')
        try:
            with open(os.path.join(BASE, 'web', 'data', 'stats.json')) as f:
                stats = json.load(f)
            with ui.row().classes('gap-6'):
                for label, val in [('Charts', stats['charts']), ('Audio', stats['audio_files']),
                                   ('Players', stats['players']),
                                   ('Pattern Windows', f"{stats['pattern_windows']:,}")]:
                    with ui.card().classes('p-4'):
                        ui.label(str(val)).classes('text-3xl font-bold text-blue-400')
                        ui.label(label).classes('text-sm text-gray-400')
        except:
            ui.label('Stats not yet generated').classes('text-gray-400')


@ui.page('/leaderboard')
def leaderboard_page():
    ui.dark_mode().enable()

    nav_header()

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Umiyuri Pattern Leaderboard').classes('text-2xl font-bold mb-2')

        leaderboard_file = os.path.join(BASE, 'umiyuri_leaderboard.json')
        if not os.path.exists(leaderboard_file):
            ui.label('Leaderboard not yet generated.').classes('text-red-400')
            return

        with open(leaderboard_file, encoding='utf-8') as f:
            leaderboard = json.load(f)

        # Cycles toggle
        lb_cycles = ui.select(
            {2: '2+ cycles (R&D — 1043 charts)', 4: '4+ cycles (strict — 269 charts)'},
            value=4, label='Min cycles'
        ).classes('w-64 mb-4')

        stats_container = ui.column().classes('w-full')
        table_container = ui.column().classes('w-full')
        bottom_container = ui.column().classes('w-full')

        def refresh_leaderboard():
            score_key = f'score_{lb_cycles.value}'
            sections_key = f'sections_{lb_cycles.value}'

            # Fallback for old format
            if score_key not in leaderboard[0]:
                score_key = 'umiyuri_score'
                sections_key = 'sections'

            sorted_lb = sorted(leaderboard, key=lambda r: -r.get(score_key, 0))
            with_umiyuri = [r for r in sorted_lb if r.get(score_key, 0) > 0]
            without = [r for r in sorted_lb if r.get(score_key, 0) == 0]

            stats_container.clear()
            with stats_container:
                with ui.row().classes('gap-6 mb-4'):
                    with ui.card().classes('p-4'):
                        ui.label(str(len(with_umiyuri))).classes('text-3xl font-bold text-green-400')
                        ui.label('Charts with Umiyuri').classes('text-sm text-gray-400')
                    with ui.card().classes('p-4'):
                        ui.label(str(len(without))).classes('text-3xl font-bold text-gray-500')
                        ui.label('Charts without').classes('text-sm text-gray-400')
                    with ui.card().classes('p-4'):
                        if with_umiyuri:
                            avg = sum(r.get(score_key, 0) for r in with_umiyuri) / len(with_umiyuri)
                            ui.label(f'{avg:.1%}').classes('text-3xl font-bold text-blue-400')
                        ui.label('Avg score (when present)').classes('text-sm text-gray-400')

            table_container.clear()
            with table_container:
                ui.label('Top Umiyuri Charts').classes('text-lg font-bold mt-4 mb-2')
                top_rows = []
                for i, r in enumerate(with_umiyuri):
                    level_val = 0
                    try: level_val = float(str(r['level']).rstrip('?'))
                    except: pass
                    flag = ' ⚠' if level_val < 12.6 and level_val > 0 else ''
                    top_rows.append({
                        'rank': i + 1,
                        'title': r['title'] + flag,
                        'diff': r.get('diff_name', 'Master'),
                        'artist': r['artist'],
                        'level': r['level'],
                        'bpm': r['bpm'],
                        'notes': r['note_count'],
                        'score': f"{r.get(score_key, 0):.1%}",
                        'sections': r.get(sections_key, 0),
                    })
                ui.table(columns=top_columns, rows=top_rows, row_key='rank',
                         pagination={'rowsPerPage': 25}).classes('w-full').props('dense')

            bottom_container.clear()
            with bottom_container:
                ui.label('Lowest Non-Zero Umiyuri Charts').classes('text-lg font-bold mt-6 mb-2')
                bottom_rows = []
                for i, r in enumerate(reversed(with_umiyuri)):
                    level_val = 0
                    try: level_val = float(str(r['level']).rstrip('?'))
                    except: pass
                    flag = ' ⚠' if level_val < 12.6 and level_val > 0 else ''
                    bottom_rows.append({
                        'rank': len(with_umiyuri) - i,
                        'title': r['title'] + flag,
                        'diff': r.get('diff_name', 'Master'),
                        'artist': r['artist'],
                        'level': r['level'],
                        'bpm': r['bpm'],
                        'notes': r['note_count'],
                        'score': f"{r.get(score_key, 0):.1%}",
                        'sections': r.get(sections_key, 0),
                    })
                ui.table(columns=top_columns, rows=bottom_rows, row_key='rank',
                         pagination={'rowsPerPage': 25}).classes('w-full').props('dense')

        top_columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff', 'sortable': True},
            {'name': 'artist', 'label': 'Artist', 'field': 'artist'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'notes', 'label': 'Notes', 'field': 'notes', 'sortable': True},
            {'name': 'score', 'label': 'Umiyuri %', 'field': 'score', 'sortable': True},
            {'name': 'sections', 'label': 'Sections', 'field': 'sections', 'sortable': True},
        ]

        lb_cycles.on_value_change(lambda: refresh_leaderboard())
        # Initial render
        refresh_leaderboard()


@ui.page('/paika')
def paika_page():
    ui.dark_mode().enable()
    nav_header()

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('拍滑 (Tap-Slide) Detector').classes('text-2xl font-bold mb-2')
        ui.label('The foundational tap+slide mechanic — one hand taps, one hand slides.').classes('text-gray-400 mb-4')

        # Song selector
        song_options = {title: title for title in sorted(SONG_INDEX.keys())}
        default_song = next((t for t in SONG_INDEX if t == 'Future[SD]'), list(SONG_INDEX.keys())[0])

        with ui.row().classes('w-full items-end gap-4 mb-4'):
            song_select = ui.select(song_options, value=default_song, label='Song',
                                     with_input=True).classes('flex-grow').props('use-input input-debounce=300')
            diff_select = ui.select({2: 'Basic', 3: 'Advanced', 4: 'Expert', 5: 'Master', 6: 'Re:Master'},
                                     value=6, label='Difficulty').classes('w-40')
            analyze_btn = ui.button('Analyze', icon='search')

        results_container = ui.column().classes('w-full')

        def run_paika():
            results_container.clear()
            title = song_select.value
            path = SONG_INDEX.get(title)
            diff = diff_select.value

            if not path or not os.path.exists(path):
                with results_container:
                    ui.label(f'Song not found: {title}').classes('text-red-400')
                return

            try:
                meta, notes, level, actual_diff = load_chart(path, diff)
            except Exception as e:
                with results_container:
                    ui.label(f'Parse error: {e}').classes('text-red-400')
                return

            dets = detect_paika(notes)
            score = paika_score(notes)

            with results_container:
                with ui.card().classes('w-full mb-4'):
                    ui.label(f'{meta.title}').classes('text-xl font-bold')
                    ui.label(f'{meta.artist} | BPM {meta.bpm} | Lv.{level} | {len(notes)} notes').classes('text-gray-400')

                with ui.card().classes('w-full mb-4'):
                    ui.label('拍滑 Detection').classes('text-lg font-bold mb-2')
                    if dets:
                        with ui.row().classes('items-center gap-4 mb-2'):
                            ui.label(f'{score:.0%}').classes('text-3xl font-bold text-cyan-400')
                            ui.label('of chart is 拍滑').classes('text-gray-400')
                            ui.label(f'{len(dets)} sections').classes('text-blue-400')

                        for i, d in enumerate(dets):
                            slides_unique = list(set(d['slides'][:4]))
                            extra = f'... +{len(d["slides"])-4}' if len(d['slides']) > 4 else ''
                            ui.label(
                                f"[{i+1}] {d['start_s']:.1f}s – {d['end_s']:.1f}s "
                                f"({d['duration_s']:.1f}s, {d['count']} groups) "
                                f"Slides: {', '.join(slides_unique)}{extra}"
                            ).classes('text-sm text-gray-300 ml-4')
                    else:
                        ui.label('No 拍滑 detected').classes('text-gray-500')

                # Timeline visualization
                song_end_s = max(n.time_ms for n in notes) / 1000.0 if notes else 0

                # Build density data from windows
                results_w = analyze_chart_patterns(notes)
                timeline = get_pattern_timeline(results_w)
                density_data = [[t['time'], t['density']] for t in timeline]

                # Mark areas for 拍滑
                paika_mark_areas = []
                for d in dets:
                    paika_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(6, 182, 212, 0.2)'}},
                        {'xAxis': d['end_s']},
                    ])

                # Also detect Umiyuri for overlay
                u_dets = detect_umiyuri(notes)
                u_score = umiyuri_score(notes)
                umiyuri_mark_areas = []
                for d in u_dets:
                    umiyuri_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(34, 197, 94, 0.2)'}},
                        {'xAxis': d['end_s']},
                    ])

                ui.echart({
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['density', '拍滑', 'Umiyuri'], 'textStyle': {'color': '#999'}},
                    'grid': {'top': 40, 'bottom': 40, 'left': 60, 'right': 20},
                    'xAxis': {'type': 'value', 'name': 'Time (s)',
                              'min': 0, 'max': round(song_end_s + 1),
                              'nameTextStyle': {'color': '#999'},
                              'axisLabel': {'color': '#999'}},
                    'yAxis': {'type': 'value', 'name': 'Density',
                              'axisLabel': {'color': '#999'}},
                    'series': [
                        {
                            'name': 'density',
                            'type': 'line',
                            'data': density_data,
                            'lineStyle': {'color': '#ffffff44', 'width': 1},
                            'itemStyle': {'color': '#ffffff44'},
                            'symbol': 'none',
                            'markArea': {
                                'silent': True,
                                'data': paika_mark_areas,
                                'label': {'show': True, 'position': 'insideTop',
                                          'formatter': '拍滑', 'color': '#06b6d4',
                                          'fontSize': 10},
                            } if paika_mark_areas else {},
                        },
                        {
                            'name': 'Umiyuri',
                            'type': 'line',
                            'data': [],
                            'markArea': {
                                'silent': True,
                                'data': umiyuri_mark_areas,
                                'label': {'show': True, 'position': 'insideBottom',
                                          'formatter': 'ウミユリ', 'color': '#22c55e',
                                          'fontSize': 10},
                            } if umiyuri_mark_areas else {},
                        },
                    ],
                }).classes('w-full h-64')

                # Umiyuri comparison summary
                if u_dets:
                    with ui.row().classes('items-center gap-4 mt-2'):
                        ui.label('Also detected:').classes('text-gray-500')
                        ui.label(f'Umiyuri {u_score:.0%}').classes('text-green-400 font-bold')
                        ui.label(f'({len(u_dets)} sections)').classes('text-gray-500')

        analyze_btn.on_click(run_paika)
        run_paika()

        # Paika leaderboard
        paika_lb_file = os.path.join(BASE, 'paika_leaderboard.json')
        if os.path.exists(paika_lb_file):
            ui.label('Top 拍滑 Charts').classes('text-lg font-bold mt-6 mb-2')
            with open(paika_lb_file, encoding='utf-8') as f:
                paika_lb = json.load(f)

            columns = [
                {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
                {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
                {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
                {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
                {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
                {'name': 'score', 'label': '拍滑 %', 'field': 'score', 'sortable': True},
                {'name': 'sections', 'label': 'Sections', 'field': 'sections', 'sortable': True},
            ]
            rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                      'level': r['level'], 'bpm': r['bpm'],
                      'score': f"{r['paika_score']:.1%}", 'sections': r['sections']}
                     for i, r in enumerate(paika_lb)]
            ui.table(columns=columns, rows=rows, row_key='rank',
                     pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


@ui.page('/players')
def players_page():
    ui.dark_mode().enable()
    nav_header()

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Player Analysis').classes('text-2xl font-bold mb-2')
        ui.label('Cross-reference player scores with chart pattern profiles.').classes('text-gray-400 mb-4')

        # Load player files
        score_dir = os.path.join(BASE, 'maimai-scores', 'maimai-scores')
        player_files = sorted(glob.glob(os.path.join(score_dir, '*.json'))) if os.path.exists(score_dir) else []

        if not player_files:
            ui.label('No player score files found.').classes('text-red-400')
            return

        # Build player list
        players = {}
        for f in player_files:
            basename = os.path.basename(f).replace('.json', '')
            parts = basename.split('-')
            rating = int(parts[-1])
            name = parts[-2]
            players[f'{name} ({rating})'] = f

        player_select = ui.select(players, label='Player',
                                   with_input=True).classes('w-full mb-4').props('use-input')

        results_container = ui.column().classes('w-full')

        # Load profiles
        profiles_path = os.path.join(BASE, 'song_profiles.json')
        umiyuri_path = os.path.join(BASE, 'umiyuri_leaderboard.json')

        def analyze_player():
            results_container.clear()
            filepath = player_select.value
            if not filepath:
                return

            with open(filepath) as f:
                scores = json.load(f)

            basename = os.path.basename(filepath).replace('.json', '')
            parts = basename.split('-')
            rating = int(parts[-1])
            name = parts[-2]

            # Load profiles for matching
            song_profiles = {}
            if os.path.exists(profiles_path):
                with open(profiles_path) as f:
                    song_profiles = json.load(f)

            umiyuri_scores = {}
            if os.path.exists(umiyuri_path):
                with open(umiyuri_path) as f:
                    for r in json.load(f):
                        key = r['title']
                        s = r.get('score_4', 0)
                        if key not in umiyuri_scores or s > umiyuri_scores[key]:
                            umiyuri_scores[key] = s

            with results_container:
                with ui.card().classes('w-full mb-4'):
                    ui.label(f'{name}').classes('text-xl font-bold')
                    ui.label(f'Rating: {rating} | {len(scores)} scores').classes('text-gray-400')

                # Level performance
                level_scores = defaultdict(list)
                for s in scores:
                    level_scores[int(s['level'])].append(s['achievement'])

                with ui.card().classes('w-full mb-4'):
                    ui.label('Level Performance').classes('text-lg font-bold mb-2')
                    level_data = []
                    avg_data = []
                    for lvl in sorted(level_scores.keys()):
                        achs = level_scores[lvl]
                        avg = sum(achs) / len(achs)
                        level_data.append([lvl, len(achs)])
                        avg_data.append([lvl, round(avg, 2)])

                    ui.echart({
                        'tooltip': {'trigger': 'axis'},
                        'legend': {'data': ['Count', 'Avg %'], 'textStyle': {'color': '#999'}},
                        'xAxis': {'type': 'value', 'name': 'Level', 'axisLabel': {'color': '#999'}},
                        'yAxis': [
                            {'type': 'value', 'name': 'Count', 'axisLabel': {'color': '#999'}},
                            {'type': 'value', 'name': 'Avg %', 'min': 80, 'max': 101,
                             'position': 'right', 'axisLabel': {'color': '#999'}},
                        ],
                        'series': [
                            {'name': 'Count', 'type': 'bar', 'data': level_data,
                             'itemStyle': {'color': '#3b82f6'}},
                            {'name': 'Avg %', 'type': 'line', 'yAxisIndex': 1, 'data': avg_data,
                             'lineStyle': {'color': '#22c55e'}, 'itemStyle': {'color': '#22c55e'}},
                        ],
                    }).classes('w-full h-64')

                # Pattern performance
                pattern_names = ['拍滑', 'stream', 'jacks', 'cross_hand', 'slide_heavy', 'each_heavy', 'rotation']

                import re
                def norm(n):
                    return re.sub(r'\[(?:SD|DX)\]', '', n).strip().lower()

                norm_lookup = {}
                for song, profile in song_profiles.items():
                    norm_lookup[norm(song)] = profile

                with ui.card().classes('w-full mb-4'):
                    ui.label('Pattern Performance').classes('text-lg font-bold mb-2')

                    pattern_results = {}
                    for pname in pattern_names:
                        psongs = []
                        for s in scores:
                            sn = norm(s['songName'])
                            profile = norm_lookup.get(sn, {})
                            if profile.get(pname, 0) > 0.15:
                                psongs.append(s['achievement'])
                        if psongs:
                            pattern_results[pname] = sum(psongs) / len(psongs)

                    if pattern_results:
                        sorted_patterns = sorted(pattern_results.items(), key=lambda x: x[1])
                        for pname, avg in sorted_patterns:
                            color = 'red' if avg < 95 else 'yellow' if avg < 98 else 'green'
                            with ui.row().classes('items-center gap-2'):
                                ui.label(f'{pname}').classes('w-32')
                                ui.linear_progress(value=avg/101).classes('flex-grow').props(f'size=20px color={color}')
                                ui.label(f'{avg:.2f}%').classes('text-xs text-gray-400 w-16')

                # Rating improvement
                with ui.card().classes('w-full mb-4'):
                    ui.label('Rating Improvement Candidates').classes('text-lg font-bold mb-2')

                    candidates = []
                    for s in scores:
                        ach = s['achievement']
                        for threshold, rank in [(100.5, 'SSS+'), (100.0, 'SSS'), (99.5, 'SS+'),
                                                 (99.0, 'SS'), (98.0, 'S+'), (97.0, 'S')]:
                            if ach < threshold and threshold - ach <= 1.0:
                                candidates.append({
                                    'song': s['songName'], 'level': s['level'],
                                    'current': ach, 'target_rank': rank,
                                    'gap': threshold - ach,
                                })
                                break
                    candidates.sort(key=lambda x: (-x['level'], x['gap']))

                    if candidates:
                        cols = [
                            {'name': 'song', 'label': 'Song', 'field': 'song'},
                            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
                            {'name': 'current', 'label': 'Current', 'field': 'current', 'sortable': True},
                            {'name': 'target', 'label': 'Target', 'field': 'target'},
                            {'name': 'gap', 'label': 'Gap', 'field': 'gap', 'sortable': True},
                        ]
                        rows = [{'song': c['song'][:35], 'level': c['level'],
                                 'current': f"{c['current']:.2f}%",
                                 'target': c['target_rank'], 'gap': f"{c['gap']:.2f}%"}
                                for c in candidates[:20]]
                        ui.table(columns=cols, rows=rows, row_key='song',
                                 pagination={'rowsPerPage': 10}).classes('w-full').props('dense')

        player_select.on_value_change(lambda: analyze_player())


@ui.page('/map')
def map_page():
    ui.dark_mode().enable()
    nav_header()

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Chart Archetype Map').classes('text-2xl font-bold mb-2')
        ui.label('1,618 charts embedded in 2D using UMAP. Each point is a chart.').classes('text-gray-400 mb-4')

        embedding_file = os.path.join(BASE, 'chart_embedding.json')
        if not os.path.exists(embedding_file):
            ui.label('Chart embedding not generated yet.').classes('text-red-400')
            return

        with open(embedding_file, encoding='utf-8') as f:
            data = json.load(f)

        color_select = ui.select(
            {'level': 'Level', 'umiyuri': 'Umiyuri %', 'paika': '拍滑 %',
             'density': 'Note Density', 'slide_ratio': 'Slide Ratio'},
            value='level', label='Color by'
        ).classes('w-48 mb-4')

        chart_container = ui.column().classes('w-full')

        def render_map():
            chart_container.clear()
            color_by = color_select.value
            vals = [d.get(color_by, 0) for d in data]
            max_val = max(vals) if vals else 1
            min_val = min(vals) if vals else 0

            with chart_container:
                ui.echart({
                    'tooltip': {
                        'trigger': 'item',
                        'formatter': None,  # will use default
                    },
                    'visualMap': {
                        'min': min_val, 'max': max_val,
                        'dimension': 2,
                        'inRange': {'color': ['#1a1a2e', '#16213e', '#0f3460', '#e94560']},
                        'textStyle': {'color': '#999'},
                        'text': [f'{color_by} (high)', f'{color_by} (low)'],
                    },
                    'xAxis': {'show': False},
                    'yAxis': {'show': False},
                    'series': [{
                        'type': 'scatter',
                        'data': [[d['x'], d['y'], d.get(color_by, 0)] for d in data],
                        'symbolSize': 5,
                    }],
                }).classes('w-full h-[600px]')

        color_select.on_value_change(lambda: render_map())
        render_map()


import glob


@ui.page('/slide-reading')
def slide_reading_page():
    ui.dark_mode().enable()
    nav_header()

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Slide Reading Detector').classes('text-2xl font-bold mb-2')
        ui.label('Taps placed during the 1-beat slide delay — beginners miss these because they treat slides as separate from taps.').classes('text-gray-400 mb-4')

        song_options = {title: title for title in sorted(SONG_INDEX.keys())}
        default_song = next((t for t in SONG_INDEX if 'ECHO' in t and 'SD' in t), list(SONG_INDEX.keys())[0])

        with ui.row().classes('w-full items-end gap-4 mb-4'):
            song_select = ui.select(song_options, value=default_song, label='Song',
                                     with_input=True).classes('flex-grow').props('use-input input-debounce=300')
            diff_select = ui.select({2: 'Basic', 3: 'Advanced', 4: 'Expert', 5: 'Master', 6: 'Re:Master'},
                                     value=5, label='Difficulty').classes('w-40')
            analyze_btn = ui.button('Analyze', icon='search')

        results_container = ui.column().classes('w-full')

        def run_sr():
            results_container.clear()
            title = song_select.value
            path = SONG_INDEX.get(title)
            diff = diff_select.value

            if not path or not os.path.exists(path):
                with results_container:
                    ui.label(f'Song not found').classes('text-red-400')
                return

            try:
                meta, notes, level, actual_diff = load_chart(path, diff)
            except Exception as e:
                with results_container:
                    ui.label(f'Parse error: {e}').classes('text-red-400')
                return

            sr_dets = detect_slide_reading(notes)
            sr_score = slide_reading_score(notes)
            p_score = paika_score(notes)

            with results_container:
                with ui.card().classes('w-full mb-4'):
                    ui.label(f'{meta.title}').classes('text-xl font-bold')
                    ui.label(f'{meta.artist} | BPM {meta.bpm} | Lv.{level} | {len(notes)} notes').classes('text-gray-400')

                with ui.row().classes('gap-4 mb-4'):
                    with ui.card().classes('p-4'):
                        ui.label(f'{sr_score:.0%}').classes('text-3xl font-bold text-orange-400')
                        ui.label('Slide Reading').classes('text-sm text-gray-400')
                    with ui.card().classes('p-4'):
                        ui.label(f'{p_score:.0%}').classes('text-3xl font-bold text-cyan-400')
                        ui.label('拍滑 (simultaneous)').classes('text-sm text-gray-400')

                if sr_dets:
                    for i, d in enumerate(sr_dets):
                        ui.label(
                            f"[{i+1}] {d['start_s']:.1f}s – {d['end_s']:.1f}s ({d['count']} events)"
                        ).classes('text-sm text-gray-300 ml-4')

                # Timeline
                song_end_s = max(n.time_ms for n in notes) / 1000.0 if notes else 0
                results_w = analyze_chart_patterns(notes)
                timeline = get_pattern_timeline(results_w)
                density_data = [[t['time'], t['density']] for t in timeline]

                sr_marks = [[{'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(251, 146, 60, 0.2)'}},
                             {'xAxis': d['end_s']}] for d in sr_dets]
                p_dets = detect_paika(notes)
                p_marks = [[{'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(6, 182, 212, 0.15)'}},
                            {'xAxis': d['end_s']}] for d in p_dets]

                ui.echart({
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': ['density'], 'textStyle': {'color': '#999'}},
                    'grid': {'top': 40, 'bottom': 40, 'left': 60, 'right': 20},
                    'xAxis': {'type': 'value', 'min': 0, 'max': round(song_end_s + 1),
                              'name': 'Time (s)', 'axisLabel': {'color': '#999'}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': '#999'}},
                    'series': [
                        {'name': 'density', 'type': 'line', 'data': density_data,
                         'lineStyle': {'color': '#ffffff44'}, 'symbol': 'none',
                         'markArea': {'silent': True, 'data': sr_marks,
                                      'label': {'show': True, 'position': 'insideTop',
                                                'formatter': 'Reading', 'color': '#fb923c', 'fontSize': 10}}
                         if sr_marks else {}},
                        {'name': '拍滑', 'type': 'line', 'data': [],
                         'markArea': {'silent': True, 'data': p_marks,
                                      'label': {'show': True, 'position': 'insideBottom',
                                                'formatter': '拍滑', 'color': '#06b6d4', 'fontSize': 10}}
                         if p_marks else {}},
                    ],
                }).classes('w-full h-64')

        analyze_btn.on_click(run_sr)
        run_sr()

        # Leaderboard
        sr_lb_file = os.path.join(BASE, 'slide_reading_leaderboard.json')
        if os.path.exists(sr_lb_file):
            ui.label('Top Slide Reading Charts').classes('text-lg font-bold mt-6 mb-2')
            with open(sr_lb_file, encoding='utf-8') as f:
                sr_lb = json.load(f)
            columns = [
                {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
                {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
                {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
                {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
                {'name': 'score', 'label': 'Score', 'field': 'score', 'sortable': True},
            ]
            rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                      'level': r['level'], 'score': f"{r['slide_reading_score']:.1%}"}
                     for i, r in enumerate(sr_lb)]
            ui.table(columns=columns, rows=rows, row_key='rank',
                     pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


@ui.page('/rotation')
def rotation_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('轉圈/掃鍵 Leaderboard (Rotation / Sweeping)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest continuous directional tap run. 1 cycle = 8 buttons around the circle.').classes('text-gray-400 mb-4')
        stream_lb_file = os.path.join(BASE, 'stream_leaderboard.json')
        if not os.path.exists(stream_lb_file): return
        with open(stream_lb_file, encoding='utf-8') as f:
            stream_lb = json.load(f)
        multi = [s for s in stream_lb if s['cycles'] >= 2]
        with ui.row().classes('gap-6 mb-4'):
            with ui.card().classes('p-4'):
                ui.label(str(len(stream_lb))).classes('text-3xl font-bold text-blue-400')
                ui.label('Charts with 1+ cycle').classes('text-sm text-gray-400')
            with ui.card().classes('p-4'):
                ui.label(str(len(multi))).classes('text-3xl font-bold text-orange-400')
                ui.label('Charts with 2+ cycles').classes('text-sm text-gray-400')
            if stream_lb:
                with ui.card().classes('p-4'):
                    ui.label(f"{stream_lb[0]['cycles']}x").classes('text-3xl font-bold text-red-400')
                    ui.label(f"Max: {stream_lb[0]['title'][:20]}").classes('text-sm text-gray-400')
        columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'run', 'label': 'Run', 'field': 'run', 'sortable': True},
            {'name': 'cycles', 'label': 'Cycles', 'field': 'cycles', 'sortable': True},
        ]
        rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                 'level': r['level'], 'bpm': r['bpm'],
                 'run': r['longest_run'], 'cycles': f"{r['cycles']}x"}
                for i, r in enumerate(stream_lb)]
        ui.table(columns=columns, rows=rows, row_key='rank',
                 pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


@ui.page('/jacks')
def jacks_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('縦連 Leaderboard (Jacks)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest consecutive same-position tap run.').classes('text-gray-400 mb-4')
        jack_lb_file = os.path.join(BASE, 'jack_leaderboard.json')
        if not os.path.exists(jack_lb_file): return
        with open(jack_lb_file, encoding='utf-8') as f:
            jack_lb = json.load(f)
        long_jacks = [j for j in jack_lb if j['longest_jack'] >= 10]
        with ui.row().classes('gap-6 mb-4'):
            with ui.card().classes('p-4'):
                ui.label(str(len(jack_lb))).classes('text-3xl font-bold text-blue-400')
                ui.label('Charts with 4+ jacks').classes('text-sm text-gray-400')
            with ui.card().classes('p-4'):
                ui.label(str(len(long_jacks))).classes('text-3xl font-bold text-yellow-400')
                ui.label('Charts with 10+ jacks').classes('text-sm text-gray-400')
            if jack_lb:
                with ui.card().classes('p-4'):
                    ui.label(str(jack_lb[0]['longest_jack'])).classes('text-3xl font-bold text-red-400')
                    ui.label(f"Max: {jack_lb[0]['title'][:25]}").classes('text-sm text-gray-400')
        columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'hits', 'label': 'Hits', 'field': 'hits', 'sortable': True},
        ]
        rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                 'level': r['level'], 'bpm': r['bpm'], 'hits': r['longest_jack']}
                for i, r in enumerate(jack_lb)]
        ui.table(columns=columns, rows=rows, row_key='rank',
                 pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


@ui.page('/trills')
def trills_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('トリル/交差 Leaderboard (Trills / Cross-hand)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest alternating two-position run. ✕ = cross-hand (distance ≥ 3 positions apart).').classes('text-gray-400 mb-4')
        trill_lb_file = os.path.join(BASE, 'trill_leaderboard.json')
        if not os.path.exists(trill_lb_file): return
        with open(trill_lb_file, encoding='utf-8') as f:
            trill_lb = json.load(f)
        cross_only = ui.switch('Cross-hand only (distance ≥ 3)').classes('mb-4')
        trill_container = ui.column().classes('w-full')
        def refresh_trills():
            trill_container.clear()
            filtered = [r for r in trill_lb if r['cross_hand']] if cross_only.value else trill_lb
            with trill_container:
                with ui.row().classes('gap-6 mb-4'):
                    with ui.card().classes('p-4'):
                        ui.label(str(len(filtered))).classes('text-3xl font-bold text-blue-400')
                        ui.label('Charts').classes('text-sm text-gray-400')
                    if filtered:
                        with ui.card().classes('p-4'):
                            ui.label(str(filtered[0]['longest_trill'])).classes('text-3xl font-bold text-red-400')
                            ui.label(f"Max: {filtered[0]['title'][:25]}").classes('text-sm text-gray-400')
                columns = [
                    {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
                    {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
                    {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
                    {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
                    {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
                    {'name': 'hits', 'label': 'Hits', 'field': 'hits', 'sortable': True},
                    {'name': 'pos', 'label': 'Positions', 'field': 'pos'},
                    {'name': 'dist', 'label': 'Dist', 'field': 'dist', 'sortable': True},
                ]
                rows = [{'rank': i+1, 'title': ('✕ ' if r['cross_hand'] else '') + r['title'],
                         'diff': r['diff_name'], 'level': r['level'], 'bpm': r['bpm'],
                         'hits': r['longest_trill'], 'pos': r['positions'], 'dist': r['distance']}
                        for i, r in enumerate(filtered)]
                ui.table(columns=columns, rows=rows, row_key='rank',
                         pagination={'rowsPerPage': 25}).classes('w-full').props('dense')
        cross_only.on_value_change(lambda: refresh_trills())
        refresh_trills()


@ui.page('/randaa')
def randaa_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('乱打/散打 Leaderboard (Scattered)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest non-directional rapid tap run. Direction changes ≥ 30% of run length.').classes('text-gray-400 mb-4')
        randaa_lb_file = os.path.join(BASE, 'randaa_leaderboard.json')
        if not os.path.exists(randaa_lb_file): return
        with open(randaa_lb_file, encoding='utf-8') as f:
            randaa_lb = json.load(f)
        with ui.row().classes('gap-6 mb-4'):
            with ui.card().classes('p-4'):
                ui.label(str(len(randaa_lb))).classes('text-3xl font-bold text-blue-400')
                ui.label('Charts detected').classes('text-sm text-gray-400')
            if randaa_lb:
                with ui.card().classes('p-4'):
                    ui.label(str(randaa_lb[0]['longest_randaa'])).classes('text-3xl font-bold text-red-400')
                    ui.label(f"Max: {randaa_lb[0]['title'][:25]}").classes('text-sm text-gray-400')
        columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'hits', 'label': 'Hits', 'field': 'hits', 'sortable': True},
        ]
        rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                 'level': r['level'], 'bpm': r['bpm'], 'hits': r['longest_randaa']}
                for i, r in enumerate(randaa_lb)]
        ui.table(columns=columns, rows=rows, row_key='rank',
                 pagination={'rowsPerPage': 25}).classes('w-full').props('dense')




@ui.page('/hitofude')
def hitofude_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('一筆畫 Leaderboard (One-Stroke Slides)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest chain of slides where each endpoint is the next start. Continuous drawing without lifting.').classes('text-gray-400 mb-4')
        lb_file = os.path.join(BASE, 'hitofude_leaderboard.json')
        if not os.path.exists(lb_file): return
        with open(lb_file, encoding='utf-8') as f:
            lb = json.load(f)
        with ui.row().classes('gap-6 mb-4'):
            with ui.card().classes('p-4'):
                ui.label(str(len(lb))).classes('text-3xl font-bold text-blue-400')
                ui.label('Charts detected').classes('text-sm text-gray-400')
            if lb:
                with ui.card().classes('p-4'):
                    ui.label(str(lb[0]['longest_chain'])).classes('text-3xl font-bold text-red-400')
                    ui.label(f"Max: {lb[0]['title'][:25]}").classes('text-sm text-gray-400')
        columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'chain', 'label': 'Chain', 'field': 'chain', 'sortable': True},
        ]
        rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                 'level': r['level'], 'bpm': r['bpm'], 'chain': r['longest_chain']}
                for i, r in enumerate(lb)]
        ui.table(columns=columns, rows=rows, row_key='rank',
                 pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


@ui.page('/mahoujin')
def mahoujin_page():
    ui.dark_mode().enable()
    nav_header()
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('魔法陣 Leaderboard (Crossing Slides)').classes('text-2xl font-bold mb-2')
        ui.label('Ranked by longest chain of slides whose trajectories cross each other. No consecutive identical trajectories.').classes('text-gray-400 mb-4')
        lb_file = os.path.join(BASE, 'mahoujin_leaderboard.json')
        if not os.path.exists(lb_file): return
        with open(lb_file, encoding='utf-8') as f:
            lb = json.load(f)
        with ui.row().classes('gap-6 mb-4'):
            with ui.card().classes('p-4'):
                ui.label(str(len(lb))).classes('text-3xl font-bold text-blue-400')
                ui.label('Charts detected').classes('text-sm text-gray-400')
            if lb:
                with ui.card().classes('p-4'):
                    ui.label(str(lb[0]['longest_chain'])).classes('text-3xl font-bold text-red-400')
                    ui.label(f"Max: {lb[0]['title'][:25]}").classes('text-sm text-gray-400')
        columns = [
            {'name': 'rank', 'label': '#', 'field': 'rank', 'sortable': True},
            {'name': 'title', 'label': 'Title', 'field': 'title', 'sortable': True},
            {'name': 'diff', 'label': 'Diff', 'field': 'diff'},
            {'name': 'level', 'label': 'Level', 'field': 'level', 'sortable': True},
            {'name': 'bpm', 'label': 'BPM', 'field': 'bpm', 'sortable': True},
            {'name': 'chain', 'label': 'Crossings', 'field': 'chain', 'sortable': True},
        ]
        rows = [{'rank': i+1, 'title': r['title'], 'diff': r['diff_name'],
                 'level': r['level'], 'bpm': r['bpm'], 'chain': r['longest_chain']}
                for i, r in enumerate(lb)]
        ui.table(columns=columns, rows=rows, row_key='rank',
                 pagination={'rowsPerPage': 25}).classes('w-full').props('dense')


ui.run(host='0.0.0.0', port=8888, title='maimai-claude-code', reload=False)
