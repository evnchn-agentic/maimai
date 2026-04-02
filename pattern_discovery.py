#!/usr/bin/env python3
"""
Unsupervised pattern discovery for maimai charts.

Extracts features from parsed charts, windows them into fixed-length segments,
and clusters to discover recurring patterns.
"""

import json
import os
import sys
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from simai_parser import parse_maidata, parse_chart_string, Note

# ─── Feature Extraction ───

@dataclass
class TimeWindow:
    """A fixed-duration window of notes from a chart."""
    start_ms: float
    end_ms: float
    notes: List[Note]
    song_title: str = ''
    difficulty: int = 0
    level: str = ''

    @property
    def duration_ms(self):
        return self.end_ms - self.start_ms


def window_notes(notes: List[Note], window_ms: float = 2000.0,
                 step_ms: float = 500.0) -> List[TimeWindow]:
    """Sliding window over notes."""
    if not notes:
        return []
    max_time = max(n.time_ms for n in notes)
    windows = []
    t = 0.0
    while t + window_ms <= max_time + window_ms:
        w_notes = [n for n in notes if t <= n.time_ms < t + window_ms]
        if w_notes:  # skip empty windows
            windows.append(TimeWindow(
                start_ms=t,
                end_ms=t + window_ms,
                notes=w_notes,
            ))
        t += step_ms
    return windows


def extract_features(window: TimeWindow) -> Dict[str, float]:
    """Extract a feature vector from a time window."""
    notes = window.notes
    dur_s = window.duration_ms / 1000.0
    if not notes or dur_s == 0:
        return {}

    features = {}

    # ── Density ──
    features['note_density'] = len(notes) / dur_s

    # ── Note type ratios ──
    type_counts = Counter(n.note_type for n in notes)
    total = len(notes)
    for ntype in ['tap', 'hold', 'slide', 'break']:
        features[f'ratio_{ntype}'] = type_counts.get(ntype, 0) / total

    # ── Position distribution ──
    pos_counts = [0] * 8
    for n in notes:
        if 1 <= n.position <= 8:
            pos_counts[n.position - 1] += 1

    # Entropy of position distribution (how spread out across buttons)
    pos_probs = [c / total for c in pos_counts if c > 0]
    features['position_entropy'] = -sum(p * math.log2(p) for p in pos_probs) if pos_probs else 0

    # ── Simultaneous notes (Each) ──
    # Group notes by time (within 10ms tolerance)
    time_groups = defaultdict(list)
    for n in notes:
        # Round to nearest 10ms for grouping
        t_key = round(n.time_ms / 10) * 10
        time_groups[t_key].append(n)

    each_count = sum(1 for g in time_groups.values() if len(g) >= 2)
    features['each_ratio'] = each_count / max(len(time_groups), 1)

    # ── Slide features ──
    slides = [n for n in notes if n.note_type == 'slide']
    features['slide_count'] = len(slides)
    if slides:
        # Slide shape distribution
        shape_counts = Counter(n.slide_shape for n in slides)
        features['slide_shape_variety'] = len(shape_counts)
        # Arc slides (>, <, ^) vs straight (-) vs complex (p,q,s,z,v,w)
        arc_slides = sum(shape_counts.get(s, 0) for s in ['>', '<', '^'])
        straight_slides = shape_counts.get('-', 0)
        complex_slides = sum(shape_counts.get(s, 0) for s in ['p', 'pp', 'q', 'qq', 's', 'z', 'v', 'V', 'w'])
        features['slide_arc_ratio'] = arc_slides / len(slides)
        features['slide_straight_ratio'] = straight_slides / len(slides)
        features['slide_complex_ratio'] = complex_slides / len(slides)
    else:
        features['slide_shape_variety'] = 0
        features['slide_arc_ratio'] = 0
        features['slide_straight_ratio'] = 0
        features['slide_complex_ratio'] = 0

    # ── Tap+Slide simultaneous (拍滑) ──
    tap_slide_simul = 0
    for g in time_groups.values():
        types_in_group = set(n.note_type for n in g)
        if 'slide' in types_in_group and ('tap' in types_in_group or 'break' in types_in_group):
            tap_slide_simul += 1
    features['tap_slide_simultaneous'] = tap_slide_simul / max(len(time_groups), 1)

    # ── Movement / hand crossing ──
    # Sequential position deltas (how far the hand moves between notes)
    sorted_notes = sorted(notes, key=lambda n: (n.time_ms, n.position))
    if len(sorted_notes) >= 2:
        deltas = []
        for i in range(1, len(sorted_notes)):
            if sorted_notes[i].time_ms > sorted_notes[i-1].time_ms:  # only sequential
                d = abs(sorted_notes[i].position - sorted_notes[i-1].position)
                # Circular: min of clockwise and counterclockwise
                d = min(d, 8 - d)
                deltas.append(d)
        if deltas:
            features['avg_movement'] = sum(deltas) / len(deltas)
            features['max_movement'] = max(deltas)
            # Cross-hand indicator: movement >= 3 positions
            features['cross_hand_ratio'] = sum(1 for d in deltas if d >= 3) / len(deltas)
        else:
            features['avg_movement'] = 0
            features['max_movement'] = 0
            features['cross_hand_ratio'] = 0
    else:
        features['avg_movement'] = 0
        features['max_movement'] = 0
        features['cross_hand_ratio'] = 0

    # ── Rhythm regularity ──
    # How evenly spaced are the notes?
    times = sorted(set(n.time_ms for n in notes))
    if len(times) >= 3:
        intervals = [times[i+1] - times[i] for i in range(len(times)-1)]
        avg_interval = sum(intervals) / len(intervals)
        if avg_interval > 0:
            # Coefficient of variation (lower = more regular)
            variance = sum((iv - avg_interval)**2 for iv in intervals) / len(intervals)
            features['rhythm_regularity'] = 1.0 - min(math.sqrt(variance) / avg_interval, 1.0)
        else:
            features['rhythm_regularity'] = 1.0
    else:
        features['rhythm_regularity'] = 0

    # ── Directional movement (stream detection) ──
    # Are positions trending CW or CCW?
    if len(sorted_notes) >= 4:
        cw_moves = 0
        ccw_moves = 0
        for i in range(1, len(sorted_notes)):
            if sorted_notes[i].time_ms > sorted_notes[i-1].time_ms:
                diff = (sorted_notes[i].position - sorted_notes[i-1].position) % 8
                if 1 <= diff <= 3:
                    cw_moves += 1
                elif 5 <= diff <= 7:
                    ccw_moves += 1
        total_dir = cw_moves + ccw_moves
        if total_dir > 0:
            features['directional_bias'] = abs(cw_moves - ccw_moves) / total_dir
        else:
            features['directional_bias'] = 0
    else:
        features['directional_bias'] = 0

    # ── Jack detection (same position repeated) ──
    jack_count = 0
    for i in range(1, len(sorted_notes)):
        if (sorted_notes[i].time_ms > sorted_notes[i-1].time_ms and
            sorted_notes[i].position == sorted_notes[i-1].position and
            sorted_notes[i].time_ms - sorted_notes[i-1].time_ms < 200):  # within 200ms
            jack_count += 1
    features['jack_ratio'] = jack_count / max(len(sorted_notes) - 1, 1)

    return features


# ─── Batch Processing ───

def process_chart_file(filepath: str, difficulty: int = None) -> List[Tuple[TimeWindow, Dict]]:
    """Process a single maidata.txt file, return windowed features."""
    try:
        data = parse_maidata(filepath)
        meta = data['metadata']

        if not data['charts']:
            return []

        # Pick difficulty
        if difficulty and difficulty in data['charts']:
            diff = difficulty
        else:
            diff = max(data['charts'].keys())

        notes = parse_chart_string(data['charts'][diff], meta.bpm)
        if not notes:
            return []

        windows = window_notes(notes, window_ms=2000.0, step_ms=500.0)
        results = []
        for w in windows:
            w.song_title = meta.title
            w.difficulty = diff
            w.level = data.get(f'lv_{diff}', '?')
            feats = extract_features(w)
            if feats:
                results.append((w, feats))

        return results
    except Exception as e:
        return []


def find_all_charts(base_dir: str) -> List[str]:
    """Find all maidata.txt files under a directory."""
    charts = []
    for root, dirs, files in os.walk(base_dir):
        for f in files:
            if f == 'maidata.txt':
                charts.append(os.path.join(root, f))
    return charts


def batch_extract_features(chart_dir: str, difficulty: int = 5,
                           max_charts: int = None) -> Tuple[List[Dict], List[str]]:
    """Extract features from all charts in a directory.
    Returns (feature_list, feature_names)."""
    chart_files = find_all_charts(chart_dir)
    if max_charts:
        chart_files = chart_files[:max_charts]

    all_results = []
    processed = 0
    errors = 0

    for i, filepath in enumerate(chart_files):
        results = process_chart_file(filepath, difficulty)
        if results:
            for w, feats in results:
                feats['_song'] = w.song_title
                feats['_time'] = w.start_ms
                feats['_level'] = w.level
                feats['_file'] = filepath
                all_results.append(feats)
            processed += 1
        else:
            errors += 1

        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1}/{len(chart_files)} files ({processed} ok, {errors} errors)")

    print(f"Done: {processed} charts, {errors} errors, {len(all_results)} windows total")

    if all_results:
        feature_names = sorted([k for k in all_results[0].keys() if not k.startswith('_')])
        return all_results, feature_names
    return [], []


# ─── Analysis ───

def find_extreme_windows(results: List[Dict], feature_name: str,
                         top_n: int = 10, ascending: bool = False) -> List[Dict]:
    """Find windows with extreme values for a given feature."""
    valid = [r for r in results if feature_name in r]
    valid.sort(key=lambda r: r[feature_name], reverse=not ascending)
    return valid[:top_n]


def print_feature_stats(results: List[Dict], feature_names: List[str]):
    """Print statistics for each feature."""
    print(f"\n{'Feature':<30s} {'Min':>8s} {'Mean':>8s} {'Max':>8s} {'Std':>8s}")
    print('-' * 70)
    for fname in feature_names:
        vals = [r[fname] for r in results if fname in r]
        if not vals:
            continue
        mean_v = sum(vals) / len(vals)
        min_v = min(vals)
        max_v = max(vals)
        var_v = sum((v - mean_v)**2 for v in vals) / len(vals)
        std_v = math.sqrt(var_v)
        print(f"{fname:<30s} {min_v:8.3f} {mean_v:8.3f} {max_v:8.3f} {std_v:8.3f}")


def detect_pattern_candidates(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Detect windows that match known pattern signatures."""
    patterns = defaultdict(list)

    for r in results:
        # 拍滑 (tap+slide simultaneous) — Freak Out Hr pattern
        if r.get('tap_slide_simultaneous', 0) > 0.3 and r.get('slide_count', 0) >= 3:
            patterns['拍滑 (tap+slide simul)'].append(r)

        # Stream — high density, directional, regular rhythm
        if (r.get('note_density', 0) > 6 and
            r.get('directional_bias', 0) > 0.5 and
            r.get('rhythm_regularity', 0) > 0.7 and
            r.get('ratio_slide', 0) < 0.1):
            patterns['stream'].append(r)

        # Jacks — high jack ratio
        if r.get('jack_ratio', 0) > 0.3:
            patterns['縦連 (jacks)'].append(r)

        # Cross-hand heavy
        if r.get('cross_hand_ratio', 0) > 0.4:
            patterns['cross-hand'].append(r)

        # Slide-heavy (potential 一筆書き or ウミユリ)
        if r.get('ratio_slide', 0) > 0.3:
            patterns['slide-heavy'].append(r)

        # Each-heavy (lots of simultaneous notes)
        if r.get('each_ratio', 0) > 0.5:
            patterns['each-heavy'].append(r)

        # High movement (spinning/washing machine)
        if r.get('avg_movement', 0) > 3.0 and r.get('note_density', 0) > 5:
            patterns['rotation/spinning'].append(r)

    return patterns


def main():
    if len(sys.argv) < 2:
        print("Usage: python pattern_discovery.py <chart_directory> [--difficulty N] [--max N] [--patterns] [--stats]")
        sys.exit(1)

    chart_dir = sys.argv[1]
    difficulty = 5  # Master by default
    max_charts = None
    show_patterns = False
    show_stats = False

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == '--difficulty' and i + 1 < len(args):
            difficulty = int(args[i + 1])
            i += 2
        elif args[i] == '--max' and i + 1 < len(args):
            max_charts = int(args[i + 1])
            i += 2
        elif args[i] == '--patterns':
            show_patterns = True
            i += 1
        elif args[i] == '--stats':
            show_stats = True
            i += 1
        else:
            i += 1

    if not show_patterns and not show_stats:
        show_patterns = True
        show_stats = True

    print(f"Processing charts from: {chart_dir}")
    print(f"Difficulty: {difficulty}, Max charts: {max_charts or 'all'}")
    print()

    results, feature_names = batch_extract_features(chart_dir, difficulty, max_charts)

    if not results:
        print("No results!")
        sys.exit(1)

    if show_stats:
        print_feature_stats(results, feature_names)

    if show_patterns:
        print("\n" + "=" * 70)
        print("PATTERN CANDIDATES")
        print("=" * 70)
        patterns = detect_pattern_candidates(results)
        for pattern_name, windows in sorted(patterns.items(), key=lambda x: -len(x[1])):
            # Deduplicate by song
            songs = defaultdict(list)
            for w in windows:
                songs[w['_song']].append(w)

            print(f"\n── {pattern_name} ({len(windows)} windows, {len(songs)} songs) ──")
            # Show top songs by number of matching windows
            top_songs = sorted(songs.items(), key=lambda x: -len(x[1]))[:10]
            for song, wins in top_songs:
                times = [f"{w['_time']/1000:.1f}s" for w in wins[:5]]
                level = wins[0].get('_level', '?')
                print(f"  [{level:>5s}] {song}: {len(wins)} windows ({', '.join(times)}{'...' if len(wins) > 5 else ''})")

    # Save results for downstream analysis
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pattern_features.json')
    save_data = [{k: v for k, v in r.items()} for r in results]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=1)
    print(f"\nFeatures saved to {output_file} ({len(save_data)} windows)")


if __name__ == '__main__':
    main()
