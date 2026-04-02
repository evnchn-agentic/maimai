#!/usr/bin/env python3
"""
Slide reading detector — taps placed within the 1-beat delay window of a slide,
but NOT simultaneous with the star (that's 拍滑).

This detects the pattern where a tap appears an 1/8 or 1/4 note AFTER a slide star,
within the slide's delay period. Beginners fail to read these taps because they
mentally "check out" during slides and treat them as separate from the tap stream.

Distinct from 拍滑:
- 拍滑: tap simultaneous with slide star (enforcement — prevents early sliding)
- This: tap AFTER the star, during the delay (reading — beginners miss the tap)
"""

import sys
import os
from collections import defaultdict
from typing import List, Dict
from simai_parser import parse_maidata, parse_chart_string, Note


def detect_slide_reading(notes: List[Note], min_consecutive: int = 3,
                          time_tolerance_ms: float = 10.0) -> List[Dict]:
    """Detect sections with taps placed during slide delay windows (but not simultaneous).

    Looks for taps that occur AFTER a slide star tap but BEFORE the slide action begins.
    The tap must be at a different time than the star (>50ms gap) to exclude 拍滑.
    """
    if not notes:
        return []

    sorted_notes = sorted(notes, key=lambda n: n.time_ms)
    slides = [n for n in sorted_notes if n.note_type == 'slide' and n.slide_duration_ms > 0]

    # For each slide, find taps in the delay window (star_time+50ms to action_time)
    # These are the "reading challenge" taps
    reading_events = []
    for s in slides:
        window_start = s.time_ms + 50  # exclude simultaneous (拍滑)
        window_end = s.slide_action_ms - 50  # before slide starts moving, with margin to exclude next-beat taps

        if window_end <= window_start:
            continue

        taps_in_window = [n for n in sorted_notes
                          if n is not s
                          and n.note_type in ('tap', 'break')
                          and window_start <= n.time_ms <= window_end]

        if taps_in_window:
            reading_events.append({
                'time_ms': s.time_ms,
                'slide': s,
                'taps': taps_in_window,
            })

    if not reading_events:
        return []

    # Group consecutive reading events into sections
    detections = []
    i = 0
    while i < len(reading_events):
        chain_start = i
        j = i + 1

        while j < len(reading_events):
            gap = reading_events[j]['time_ms'] - reading_events[j-1]['time_ms']
            # Allow up to 2 seconds gap between events
            if gap < 2000:
                j += 1
            else:
                break

        count = j - chain_start
        if count >= min_consecutive:
            start_ms = reading_events[chain_start]['time_ms']
            end_ms = reading_events[j-1]['time_ms']

            all_slides = []
            for k in range(chain_start, j):
                s = reading_events[k]['slide']
                all_slides.append(f'{s.position}{s.slide_shape}{s.slide_end}')

            detections.append({
                'start_ms': start_ms,
                'end_ms': end_ms,
                'start_s': start_ms / 1000.0,
                'end_s': end_ms / 1000.0,
                'duration_s': (end_ms - start_ms) / 1000.0,
                'count': count,
                'slides': all_slides,
            })

        i = j if j > i else i + 1

    # Merge adjacent
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


def slide_reading_score(notes: List[Note]) -> float:
    if not notes:
        return 0.0
    detections = detect_slide_reading(notes)
    if not detections:
        return 0.0
    total_duration = max(n.time_ms for n in notes) / 1000.0
    pattern_duration = sum(d['duration_s'] for d in detections)
    return min(pattern_duration / total_duration, 1.0)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 slide_reading_detector.py <maidata.txt> [difficulty]")
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

    detections = detect_slide_reading(notes)
    score = slide_reading_score(notes)

    if detections:
        print(f"Slide reading score: {score:.1%} ({len(detections)} sections)")
        for i, d in enumerate(detections):
            print(f"  [{i+1}] {d['start_s']:.1f}s – {d['end_s']:.1f}s ({d['count']} events)")
    else:
        print("No slide reading patterns detected.")


if __name__ == '__main__':
    main()
