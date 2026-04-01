#!/usr/bin/env python3
"""
maimai-claude-code Dashboard — NiceGUI frontend.
Focused on Umiyuri pattern detection visualization.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nicegui import ui
from simai_parser import parse_maidata, parse_chart_string, Note
from pattern_discovery import (
    window_notes, extract_features, detect_pattern_candidates
)
from umiyuri_detector import detect_umiyuri, umiyuri_score
from collections import Counter, defaultdict

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
        'cross-hand': lambda r: r.get('cross_hand_ratio', 0) > 0.4,
        'slide-heavy': lambda r: r.get('ratio_slide', 0) > 0.3,
        'each-heavy': lambda r: r.get('each_ratio', 0) > 0.5,
        'rotation': lambda r: r.get('avg_movement', 0) > 3.0 and r.get('note_density', 0) > 5,
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

    with ui.header().classes('bg-blue-900'):
        ui.label('maimai-claude-code').classes('text-xl font-bold')
        ui.link('Pattern Detector', '/').classes('text-white ml-4')
        ui.link('Leaderboard', '/leaderboard').classes('text-white ml-4')
        ui.link('Pipeline Status', '/status').classes('text-white ml-4')

    # State
    state = {'chart_path': UMIYURI_PATH, 'difficulty': 5}

    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('Umiyuri Pattern Detector').classes('text-2xl font-bold mb-2')
        ui.label('Verify detected patterns against your knowledge of the chart.').classes('text-gray-400 mb-4')

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
                # Song info
                with ui.card().classes('w-full mb-4'):
                    ui.label(f'{meta.title}').classes('text-xl font-bold')
                    ui.label(f'{meta.artist} | BPM {meta.bpm} | Lv.{level} | {len(notes)} notes').classes('text-gray-400')

                # Summary stats
                type_counts = Counter(n.note_type for n in notes)
                with ui.row().classes('gap-4 mb-4'):
                    for ntype, count in type_counts.most_common():
                        with ui.card().classes('p-3'):
                            ui.label(str(count)).classes('text-2xl font-bold text-blue-400')
                            ui.label(ntype).classes('text-xs text-gray-400')

                # Pattern summary
                all_patterns = defaultdict(int)
                for t in timeline:
                    for p in t['patterns']:
                        all_patterns[p] += 1

                with ui.card().classes('w-full mb-4'):
                    ui.label('Pattern Summary').classes('text-lg font-bold mb-2')
                    for pname, count in sorted(all_patterns.items(), key=lambda x: -x[1]):
                        pct = count / len(timeline) * 100 if timeline else 0
                        with ui.row().classes('items-center gap-2'):
                            ui.label(f'{pname}').classes('w-32')
                            ui.linear_progress(value=pct/100).classes('flex-grow').props('size=20px')
                            ui.label(f'{count}/{len(timeline)} ({pct:.0f}%)').classes('text-xs text-gray-400 w-24')

                # Timeline chart (the main visualization)
                ui.label('Pattern Timeline').classes('text-lg font-bold mb-2')
                ui.label('Each row = 0.5s window. Colored bars show detected patterns.').classes('text-xs text-gray-400 mb-2')

                pattern_colors = {
                    '拍滑': '#ef4444',
                    'stream': '#3b82f6',
                    'jacks': '#f59e0b',
                    'cross-hand': '#8b5cf6',
                    'slide-heavy': '#10b981',
                    'each-heavy': '#06b6d4',
                    'rotation': '#ec4899',
                }

                # Build ECharts data
                pattern_names = list(pattern_colors.keys())
                series_data = {p: [] for p in pattern_names}

                for t in timeline:
                    time_s = t['time']
                    for p in pattern_names:
                        series_data[p].append([time_s, 1 if p in t['patterns'] else 0])

                # Density overlay
                density_data = [[t['time'], t['density']] for t in timeline]

                song_end_s = max(n.time_ms for n in notes) / 1000.0 if notes else 0

                # Build combo mapping: time_ms -> combo number
                # combo = taps(1) + breaks(1) + holds(1) + slides(2) + touches(1)
                sorted_notes_for_combo = sorted(notes, key=lambda n: (n.time_ms, n.position))
                combo_map = []  # list of (combo_number, time_ms)
                combo_num = 0
                for n in sorted_notes_for_combo:
                    combo_num += 1
                    combo_map.append((combo_num, n.time_ms))
                    if n.note_type == 'slide':
                        combo_num += 1
                        combo_map.append((combo_num, n.slide_end_ms))
                max_combo = combo_num

                def time_to_combo(time_ms):
                    """Find the combo number at a given time."""
                    best = 0
                    for c, t in combo_map:
                        if t <= time_ms:
                            best = c
                        else:
                            break
                    return best

                def combo_to_time(combo):
                    """Find the time at a given combo number."""
                    for c, t in combo_map:
                        if c >= combo:
                            return t
                    return 0

                # Umiyuri detection
                umiyuri_detections = detect_umiyuri(notes, min_cycles=cycles_select.value)
                u_score = umiyuri_score(notes)

                with ui.card().classes('w-full mb-4'):
                    ui.label('Umiyuri Pattern Detection').classes('text-lg font-bold mb-2')
                    if umiyuri_detections:
                        with ui.row().classes('items-center gap-4 mb-2'):
                            ui.label(f'{u_score:.0%}').classes('text-3xl font-bold text-green-400')
                            ui.label('of chart is Umiyuri pattern').classes('text-gray-400')
                            ui.label(f'{len(umiyuri_detections)} sections').classes('text-blue-400')
                            ui.label(f'Max combo: {max_combo}').classes('text-gray-500')

                        for i, d in enumerate(umiyuri_detections):
                            combo_start = time_to_combo(d['start_ms'])
                            combo_end = time_to_combo(d['end_ms'])
                            slide_summary = ', '.join(set(d['slides'][:4]))
                            extra = f'... +{len(d["slides"])-4}' if len(d['slides']) > 4 else ''
                            ui.label(
                                f"[{i+1}] Combo {combo_start}–{combo_end} "
                                f"({d['start_s']:.1f}s – {d['end_s']:.1f}s, "
                                f"{d['duration_s']:.1f}s, {d['cycles']} cycles) "
                                f"Slides: {slide_summary}{extra}"
                            ).classes('text-sm text-gray-300 ml-4')
                    else:
                        ui.label('No Umiyuri pattern detected').classes('text-gray-500')
                        ui.label(f'Max combo: {max_combo}').classes('text-xs text-gray-500')

                # Build mark areas for Umiyuri sections on the chart
                umiyuri_mark_areas = []
                for d in umiyuri_detections:
                    umiyuri_mark_areas.append([
                        {'xAxis': d['start_s'], 'itemStyle': {'color': 'rgba(34, 197, 94, 0.15)'}},
                        {'xAxis': d['end_s']},
                    ])

                echart_options = {
                    'tooltip': {'trigger': 'axis'},
                    'legend': {'data': pattern_names + ['density'], 'top': 0,
                               'textStyle': {'color': '#999'}},
                    'grid': {'top': 60, 'bottom': 40, 'left': 60, 'right': 20},
                    'xAxis': {'type': 'value', 'name': 'Time (s)',
                              'min': 0, 'max': round(song_end_s + 1),
                              'nameTextStyle': {'color': '#999'},
                              'axisLabel': {'color': '#999'}},
                    'yAxis': [
                        {'type': 'value', 'name': 'Pattern', 'max': 1.2,
                         'axisLabel': {'show': False}},
                        {'type': 'value', 'name': 'Density', 'position': 'right',
                         'axisLabel': {'color': '#999'}},
                    ],
                    'series': [
                        {
                            'name': p,
                            'type': 'bar',
                            'stack': 'patterns',
                            'data': series_data[p],
                            'itemStyle': {'color': pattern_colors[p]},
                            'barWidth': '90%',
                        }
                        for p in pattern_names
                    ] + [{
                        'name': 'density',
                        'type': 'line',
                        'yAxisIndex': 1,
                        'data': density_data,
                        'lineStyle': {'color': '#ffffff44', 'width': 1},
                        'itemStyle': {'color': '#ffffff44'},
                        'symbol': 'none',
                        'markArea': {
                            'silent': True,
                            'data': umiyuri_mark_areas,
                            'label': {'show': True, 'position': 'insideTop',
                                      'formatter': 'ウミユリ', 'color': '#22c55e',
                                      'fontSize': 10},
                        } if umiyuri_mark_areas else {},
                    }],
                }

                ui.echart(echart_options).classes('w-full h-96')

                # Side-by-side: mai-notes chart viewer + Umiyuri annotations
                ui.label('Chart Viewer + Umiyuri Annotations').classes('text-lg font-bold mt-4 mb-2')

                with ui.row().classes('w-full gap-4'):
                    # Left: mai-notes iframe
                    with ui.column().classes('flex-grow'):
                        ui.label('mai-notes.com Chart Viewer').classes('text-sm text-gray-400 mb-1')
                        ui.html(
                            '<iframe src="https://mai-notes.com/edit" '
                            'style="width:100%;height:700px;border:1px solid #333;border-radius:8px;" '
                            'allow="autoplay"></iframe>'
                        )

                    # Right: Umiyuri detection annotations
                    with ui.column().classes('w-80 flex-shrink-0'):
                        ui.label('Umiyuri Sections').classes('text-sm font-bold text-green-400 mb-2')

                        if umiyuri_detections:
                            for i, d in enumerate(umiyuri_detections):
                                with ui.card().classes('w-full mb-2 p-3'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.badge(f'#{i+1}', color='green')
                                        ui.label(f"{d['start_s']:.1f}s – {d['end_s']:.1f}s").classes('font-bold')
                                    ui.label(f"{d['duration_s']:.1f}s · {d['cycles']} cycles · {d.get('variant', '?')}").classes('text-xs text-gray-400')
                                    slides_unique = list(set(d['slides'][:6]))
                                    ui.label(f"Slides: {', '.join(slides_unique)}").classes('text-xs text-gray-500')
                        else:
                            ui.label('No Umiyuri sections detected').classes('text-gray-500')

                        ui.separator().classes('my-2')
                        ui.label('How to use').classes('text-xs font-bold text-gray-400')
                        ui.label(
                            'Paste the chart\'s simai data into mai-notes editor. '
                            'Compare the playback with the annotated Umiyuri sections on the right.'
                        ).classes('text-xs text-gray-500')

        analyze_btn.on_click(run_analysis)
        # Auto-run on load
        run_analysis()


@ui.page('/status')
def status_page():
    ui.dark_mode().enable()

    with ui.header().classes('bg-blue-900'):
        ui.label('maimai-claude-code').classes('text-xl font-bold')
        ui.link('Pattern Detector', '/').classes('text-white ml-4')
        ui.link('Leaderboard', '/leaderboard').classes('text-white ml-4')
        ui.link('Pipeline Status', '/status').classes('text-white ml-4')

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

    with ui.header().classes('bg-blue-900'):
        ui.label('maimai-claude-code').classes('text-xl font-bold')
        ui.link('Pattern Detector', '/').classes('text-white ml-4')
        ui.link('Leaderboard', '/leaderboard').classes('text-white ml-4')
        ui.link('Pipeline Status', '/status').classes('text-white ml-4')

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


ui.run(host='0.0.0.0', port=8888, title='maimai-claude-code', reload=False)
