#!/usr/bin/env python3
"""
拍滑 (Tap-Slide / paika) pattern detector for maimai.

拍滑 is the fundamental tap+slide mechanic where:
- A tap note at the slide's star position prevents early swiping
- The slide action begins 1 beat after the star tap
- At the moment the slide action begins, both hands are active:
  one hand taps, the other hand slides

Detection: look for each(tap+slide) groups where the tap and slide
are at the SAME time but DIFFERENT positions (one hand taps while
the other slides).

拍滑 is the building block of Umiyuri, but does NOT require the
hand-alternation cycle. It can be:
- Sustained (same pattern repeating)
- One-sided (one hand always slides, other always taps)
- Mixed with other patterns
"""

import sys
import os
from collections import defaultdict
from typing import List, Dict
from simai_parser import parse_maidata, parse_chart_string, Note


def detect_paika(notes: List[Note], min_consecutive: int = 3,
                 time_tolerance_ms: float = 10.0) -> List[Dict]:
    """Detect 拍滑 sections: each(tap+slide) groups where both hands are active.

    A group qualifies as 拍滑 if it contains both a tap/break AND a slide
    at the same timestamp, with different positions (different hands).
    """
    if not notes:
        return []

    # Group notes by time
    time_groups = defaultdict(list)
    for n in notes:
        t_key = round(n.time_ms / time_tolerance_ms) * time_tolerance_ms
        time_groups[t_key].append(n)

    sorted_times = sorted(time_groups.keys())

    # Classify each group
    group_info = []
    for t in sorted_times:
        g = time_groups[t]
        slides = [n for n in g if n.note_type == 'slide']
        taps = [n for n in g if n.note_type in ('tap', 'break')]

        is_paika = False
        if slides and taps:
            # Check: tap and slide at different positions (different hands)
            for s in slides:
                for tap in taps:
                    if tap.position != s.position:
                        is_paika = True
                        break
                if is_paika:
                    break

        group_info.append({
            'time': t,
            'notes': g,
            'is_paika': is_paika,
            'slides': slides,
            'taps': taps,
        })

    # Find consecutive runs of 拍滑 groups
    # Allow 1 non-拍滑 group between (e.g., a solo tap beat)
    detections = []
    i = 0
    while i < len(group_info):
        if not group_info[i]['is_paika']:
            i += 1
            continue

        chain_start = i
        paika_count = 0
        j = i
        gap = 0

        while j < len(group_info):
            if group_info[j]['is_paika']:
                paika_count += 1
                gap = 0
                j += 1
            elif gap < 2:
                gap += 1
                j += 1
            else:
                break

        if paika_count >= min_consecutive:
            start_ms = group_info[chain_start]['time']
            end_ms = group_info[j - 1]['time']

            all_slides = []
            for k in range(chain_start, j):
                for s in group_info[k]['slides']:
                    all_slides.append(f'{s.position}{s.slide_shape}{s.slide_end}')

            detections.append({
                'start_ms': start_ms,
                'end_ms': end_ms,
                'start_s': start_ms / 1000.0,
                'end_s': end_ms / 1000.0,
                'duration_s': (end_ms - start_ms) / 1000.0,
                'count': paika_count,
                'slides': all_slides,
            })

        i = j if j > i else i + 1

    # Merge adjacent (within 2s)
    merged = []
    for d in detections:
        if merged and d['start_ms'] - merged[-1]['end_ms'] < 2000:
            merged[-1]['end_ms'] = d['end_ms']
            merged[-1]['end_s'] = d['end_s']
            merged[-1]['duration_s'] = (merged[-1]['end_ms'] - merged[-1]['start_ms']) / 1000.0
            merged[-1]['count'] += d['count']
            merged[-1]['slides'].extend(d['slides'])
        else:
            merged.append(d)

    return merged


def paika_score(notes: List[Note]) -> float:
    """Return 0-1 score of how much of the chart is 拍滑."""
    if not notes:
        return 0.0
    detections = detect_paika(notes)
    if not detections:
        return 0.0
    total_duration = max(n.time_ms for n in notes) / 1000.0
    pattern_duration = sum(d['duration_s'] for d in detections)
    return min(pattern_duration / total_duration, 1.0)


def main():
    if len(sys.argv) < 2:
        print("Usage: python paika_detector.py <maidata.txt> [difficulty]")
        sys.exit(1)

    filepath = sys.argv[1]
    diff = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    data = parse_maidata(filepath)
    meta = data['metadata']

    if diff not in data['charts']:
        diff = max(data['charts'].keys())

    notes = parse_chart_string(data['charts'][diff], meta.bpm)
    level = data.get(f'lv_{diff}', '?')

    print(f"Title: {meta.title}")
    print(f"Difficulty: {diff} (Lv.{level})")
    print(f"Notes: {len(notes)}")
    print()

    detections = detect_paika(notes)
    score = paika_score(notes)

    if detections:
        total_dur = sum(d['duration_s'] for d in detections)
        print(f"拍滑 score: {score:.1%} ({len(detections)} sections, {total_dur:.1f}s total)")
        print()
        for i, d in enumerate(detections):
            slides_unique = list(set(d['slides'][:6]))
            extra = f'... +{len(d["slides"])-6}' if len(d['slides']) > 6 else ''
            print(f"  [{i+1}] {d['start_s']:.1f}s – {d['end_s']:.1f}s "
                  f"({d['duration_s']:.1f}s, {d['count']} groups) "
                  f"Slides: {', '.join(slides_unique)}{extra}")
    else:
        print("No 拍滑 detected.")
        print(f"拍滑 score: {score:.1%}")


if __name__ == '__main__':
    main()
