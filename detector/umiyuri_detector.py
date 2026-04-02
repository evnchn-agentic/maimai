#!/usr/bin/env python3
"""
Dedicated Umiyuri (ウミユリ/海底譚) pattern detector.

The Umiyuri pattern is alternating 拍滑 (tap+slide) where:
- Hand A: tap + slide star (queues a slide that will travel for some duration)
- Hand B: tap (or tap + another slide star)
- When Hand A's slide finishes at the endpoint, Hand A taps there
- Meanwhile Hand B's slide (if any) is being traced
- Cycle repeats, alternating hands

The key signal is: **a slide's end time coincides with (or is near) the next
tap/slide-start event**, creating an interlocking hand-coordination chain.

Detection variants:
- Classic Umiyuri: tap → each(tap+slide) → tap → each(tap+slide) alternating
- On-beat variant: tap → slide → tap → slide (solo, not each-based)
- Dense variant: each(tap+slide) → each(tap+slide) continuously (like Future)

All variants share: repeated slide notes where the pattern forms a chain.
"""

import sys
import os
from collections import defaultdict
from typing import List, Dict
from simai_parser import parse_maidata, parse_chart_string, Note


def detect_umiyuri(notes: List[Note], min_cycles: int = 4,
                   time_tolerance_ms: float = 10.0) -> List[Dict]:
    """Detect Umiyuri pattern sections in a chart.

    Looks for chains of slides interleaved with taps, where the pattern
    forms a sustained alternating hand-coordination cycle.
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
        has_slide = any(n.note_type == 'slide' for n in g)
        has_tap = any(n.note_type in ('tap', 'break') for n in g)
        has_hold = any(n.note_type == 'hold' for n in g)
        count = len(g)
        slides = [n for n in g if n.note_type == 'slide']

        group_info.append({
            'time': t,
            'notes': g,
            'has_slide': has_slide,
            'has_tap': has_tap,
            'has_hold': has_hold,
            'count': count,
            'slides': slides,
        })

    # Build a time lookup for all notes (for slide-end matching)
    all_note_times = defaultdict(list)
    for n in notes:
        t_key = round(n.time_ms / time_tolerance_ms) * time_tolerance_ms
        all_note_times[t_key].append(n)

    def has_tap_during_slide(slide_note):
        """Check if there's a tap/break note happening while this slide is in progress,
        from a DIFFERENT time group (not simultaneous each notes).
        This is the core Umiyuri signal: both hands doing independent things."""
        # Check from shortly after the star tap to slide end.
        # Include the delay period — fragrance-type umiyuri has taps during delay.
        # Exclude the first 100ms to avoid counting simultaneous each notes.
        start_ms = slide_note.time_ms + 100
        end_ms = slide_note.slide_end_ms - 30
        if end_ms <= start_ms:
            return False
        # Check all time buckets in the window
        t = start_ms
        while t <= end_ms:
            t_key = round(t / time_tolerance_ms) * time_tolerance_ms
            for n in all_note_times.get(t_key, []):
                if n is not slide_note and n.note_type in ('tap', 'break'):
                    return True
            t += time_tolerance_ms
        return False

    # Direct scan for alternating tap-slide pattern
    # Classify each group as 'T' (tap-only) or 'S' (has qualifying slide)
    group_labels = []
    for g in group_info:
        if g['has_slide']:
            # Solo slide: only counts if hand-independent activity during travel
            independence_ok = False
            for s in g['slides']:
                if s.slide_duration_ms > 0 and has_tap_during_slide(s):
                    independence_ok = True
                    break
            group_labels.append('S' if independence_ok else 's')
        elif g['has_tap']:
            group_labels.append('T')
        else:
            group_labels.append('?')

    # Scan for runs of strict T-S alternation (T,S,T,S or S,T,S,T)
    # 's' (slide without endpoint match) breaks the chain
    detections = []
    i = 0
    while i < len(group_labels):
        if group_labels[i] not in ('T', 'S'):
            i += 1
            continue

        # Try to extend an alternating chain
        chain_start = i
        j = i
        expected = group_labels[i]
        slide_count = 0

        mismatch_budget = 0  # allow skipping a few non-matching groups
        while j < len(group_labels):
            if group_labels[j] == expected:
                if expected == 'S':
                    slide_count += 1
                expected = 'S' if expected == 'T' else 'T'
                j += 1
                mismatch_budget = 1  # reset budget after a match
            elif mismatch_budget > 0 and group_labels[j] in ('T', '?'):
                # Allow skipping 1-2 non-alternating groups (bridge between sub-chains)
                mismatch_budget -= 1
                j += 1
            else:
                break

        if slide_count >= min_cycles:
            # Umiyuri check: the tap groups in the chain should include
            # single taps (one hand resting). If ALL tap groups are each (2+),
            # it's 拍滑 not Umiyuri.
            tap_groups_in_chain = [group_info[k] for k in range(chain_start, j)
                                  if group_labels[k] == 'T']
            single_tap_count = sum(1 for g in tap_groups_in_chain if g['count'] == 1)
            single_tap_ratio = single_tap_count / max(len(tap_groups_in_chain), 1)

            if single_tap_ratio < 0.3:
                # Too few single taps — this is 拍滑 (all each), not Umiyuri
                i = j if j > i else i + 1
                continue

            # Check slide variety: real Umiyuri has varied slide directions.
            # A repetitive 2-slide loop (same motif repeated) is not Umiyuri.
            all_slides = []
            for k in range(chain_start, j):
                for s in group_info[k]['slides']:
                    all_slides.append(f'{s.position}{s.slide_shape}{s.slide_end}')

            # No back-to-back identical slides allowed.
            # Real Umiyuri alternates slide directions between hands.
            # If the same slide appears consecutively, it's one hand repeating.
            has_back_to_back = False
            if len(all_slides) >= 2:
                for k in range(len(all_slides) - 1):
                    if all_slides[k] == all_slides[k + 1]:
                        has_back_to_back = True
                        break
            if has_back_to_back:
                i = j if j > i else i + 1
                continue

            # Tap position check: taps must not be stuck at one position
            # for the entire chain. Short repeats (2,2,8) are OK.
            # Long runs (3,3,3,3,6,6,6,6) are not — that's one hand hammering.
            tap_positions_seq = []
            for k in range(chain_start, j):
                if group_labels[k] == 'T':
                    for n in group_info[k]['notes']:
                        if n.note_type in ('tap', 'break'):
                            tap_positions_seq.append(n.position)
            if len(tap_positions_seq) >= 4:
                # Check: what fraction of consecutive taps are same-position?
                same_count = sum(1 for k in range(len(tap_positions_seq) - 1)
                                 if tap_positions_seq[k] == tap_positions_seq[k + 1])
                same_ratio = same_count / (len(tap_positions_seq) - 1)
                if same_ratio > 0.7:
                    # Mostly hammering same position — not Umiyuri
                    i = j if j > i else i + 1
                    continue

            # Umiyuri requires the 2-1-2-1 group size pattern.
            # Detected chains must have some size-2+ groups (the "each" component).
            # Pure all-size-1 chains are sequential slides, not hand-independent Umiyuri.
            chain_groups = [group_info[k] for k in range(chain_start, j)]
            size_2plus = sum(1 for g in chain_groups if g['count'] >= 2)
            size_2plus_ratio = size_2plus / max(len(chain_groups), 1)
            if size_2plus_ratio < 0.15:
                # Too few multi-note groups — sequential slides, not Umiyuri
                i = j if j > i else i + 1
                continue

            # Positional chain rule: in consecutive slide groups,
            # tap(group N).position == slide(group N-1).start_position
            # This is the 拍滑 interlock that defines Umiyuri.
            slide_groups_in_chain = []
            for k in range(chain_start, j):
                if group_labels[k] == 'S':
                    slides_here = [n for n in group_info[k]['notes'] if n.note_type == 'slide']
                    taps_here = [n for n in group_info[k]['notes'] if n.note_type in ('tap', 'break')]
                    if slides_here:
                        slide_groups_in_chain.append({'slides': slides_here, 'taps': taps_here})

            if len(slide_groups_in_chain) >= 2:
                # Classic Umiyuri: tap(t).position == slide(t-1).start_position
                classic_match = 0
                classic_total = 0
                # Fragrance-type: slide(t).start == slide(t-1).start (self-reinforcing)
                frag_match = 0
                frag_total = 0
                for k in range(1, len(slide_groups_in_chain)):
                    prev_slide_start = slide_groups_in_chain[k-1]['slides'][0].position
                    curr_slide_start = slide_groups_in_chain[k]['slides'][0].position
                    curr_taps = slide_groups_in_chain[k]['taps']
                    if curr_taps:
                        classic_total += 1
                        if any(t.position == prev_slide_start for t in curr_taps):
                            classic_match += 1
                    frag_total += 1
                    if curr_slide_start == prev_slide_start:
                        frag_match += 1

                classic_ratio = classic_match / max(classic_total, 1)
                frag_ratio = frag_match / max(frag_total, 1)

                if classic_ratio >= 0.5:
                    detected_variant = 'classic'
                elif frag_ratio >= 0.7:
                    detected_variant = 'fragrance-type'
                else:
                    # Neither pattern holds — not Umiyuri
                    i = j if j > i else i + 1
                    continue

            start_ms = group_info[chain_start]['time']
            end_ms = group_info[j - 1]['time']

            variant = detected_variant

            detections.append({
                'start_ms': start_ms,
                'end_ms': end_ms,
                'start_s': start_ms / 1000.0,
                'end_s': end_ms / 1000.0,
                'duration_s': (end_ms - start_ms) / 1000.0,
                'cycles': slide_count,
                'variant': variant,
                'slides': all_slides,
            })
            i = j
        else:
            i += 1

    # Merge adjacent detections (within 2s gap)
    merged = []
    for d in detections:
        if merged and d['start_ms'] - merged[-1]['end_ms'] < 2000:
            merged[-1]['end_ms'] = d['end_ms']
            merged[-1]['end_s'] = d['end_s']
            merged[-1]['duration_s'] = (merged[-1]['end_ms'] - merged[-1]['start_ms']) / 1000.0
            merged[-1]['cycles'] += d['cycles']
            merged[-1]['slides'].extend(d['slides'])
            # Keep the more specific variant
            if d['variant'] != merged[-1].get('variant'):
                merged[-1]['variant'] = 'mixed'
        else:
            merged.append(d)

    return merged


def _deprecated_detect_fragrance_type(notes: List[Note], min_cycles: int = 4,
                           time_tolerance_ms: float = 10.0) -> List[Dict]:
    """Detect Fragrance/ECHO-type umiyuri: self-reinforcing 拍滑.

    Pattern: consecutive slides starting from the SAME position, with taps
    on the opposite side. The star tap for slide N+1 prevents early swiping
    of slide N — self-reinforcing without needing a separate tap note.

    Structurally: slide(t).start == slide(t-1).start, with a tap at a
    different position in each group (the other hand).
    """
    if not notes:
        return []

    # Group notes by time
    time_groups = defaultdict(list)
    for n in notes:
        t_key = round(n.time_ms / time_tolerance_ms) * time_tolerance_ms
        time_groups[t_key].append(n)

    sorted_times = sorted(time_groups.keys())

    # Find chains of each(tap+slide) groups where slides share the same start position
    detections = []
    i = 0
    while i < len(sorted_times):
        g = time_groups[sorted_times[i]]
        slides = [n for n in g if n.note_type == 'slide']
        taps = [n for n in g if n.note_type in ('tap', 'break')]

        if not (slides and taps):
            i += 1
            continue

        # Start a chain: look for consecutive groups with same slide start + tap
        chain_start = i
        chain_slide_pos = slides[0].position
        chain_slides = []
        j = i

        while j < len(sorted_times):
            g2 = time_groups[sorted_times[j]]
            s2 = [n for n in g2 if n.note_type == 'slide']
            t2 = [n for n in g2 if n.note_type in ('tap', 'break')]

            if s2 and t2 and s2[0].position == chain_slide_pos:
                chain_slides.append({'slides': s2, 'taps': t2, 'time': sorted_times[j]})
                j += 1
            elif not s2 and t2:
                # Solo tap group between — required for alternation
                j += 1
            else:
                break

        if len(chain_slides) >= min_cycles:
            # Must have solo tap groups between slide groups (alternation)
            # If it's ALL each(tap+slide) with no solo taps, it's 拍滑 not umiyuri
            chain_region = [time_groups[sorted_times[k]] for k in range(chain_start, j)]
            solo_tap_groups = sum(1 for g in chain_region
                                  if not any(n.note_type == 'slide' for n in g)
                                  and any(n.note_type in ('tap', 'break') for n in g))
            if solo_tap_groups < len(chain_slides) * 0.3:
                i = j if j > i else i + 1
                continue
            # Verify slides have varied endpoints (not just repeating same slide)
            endpoints = [f'{s["slides"][0].slide_end}' for s in chain_slides]
            # No back-to-back same endpoint
            has_repeat = any(endpoints[k] == endpoints[k+1] for k in range(len(endpoints)-1)) if len(endpoints) >= 2 else False

            if not has_repeat:
                start_ms = chain_slides[0]['time']
                end_ms = chain_slides[-1]['time']
                all_slide_strs = [f'{s["slides"][0].position}{s["slides"][0].slide_shape}{s["slides"][0].slide_end}'
                                  for s in chain_slides]
                detections.append({
                    'start_ms': start_ms,
                    'end_ms': end_ms,
                    'start_s': start_ms / 1000.0,
                    'end_s': end_ms / 1000.0,
                    'duration_s': (end_ms - start_ms) / 1000.0,
                    'cycles': len(chain_slides),
                    'variant': 'fragrance-type',
                    'slides': all_slide_strs,
                })

        i = j if j > i else i + 1

    # Merge adjacent
    merged = []
    for d in detections:
        if merged and d['start_ms'] - merged[-1]['end_ms'] < 2000:
            merged[-1]['end_ms'] = d['end_ms']
            merged[-1]['end_s'] = d['end_s']
            merged[-1]['duration_s'] = (merged[-1]['end_ms'] - merged[-1]['start_ms']) / 1000.0
            merged[-1]['cycles'] += d['cycles']
            merged[-1]['slides'].extend(d['slides'])
        else:
            merged.append(d)

    return merged


def umiyuri_score(notes: List[Note]) -> float:
    """Return a 0-1 score of how much of the chart is Umiyuri pattern."""
    if not notes:
        return 0.0
    detections = detect_umiyuri(notes, min_cycles=4)
    if not detections:
        return 0.0
    total_duration = max(n.time_ms for n in notes) / 1000.0
    pattern_duration = sum(d['duration_s'] for d in detections)
    return min(pattern_duration / total_duration, 1.0)


def format_detections(detections: List[Dict], title: str = '') -> str:
    """Format detections for display."""
    lines = []
    if title:
        lines.append(f"=== {title} ===")
    if not detections:
        lines.append("  No Umiyuri pattern detected.")
        return '\n'.join(lines)

    total_dur = sum(d['duration_s'] for d in detections)
    lines.append(f"  {len(detections)} sections, {total_dur:.1f}s total")
    lines.append('')

    for i, d in enumerate(detections):
        slide_summary = ', '.join(set(d['slides'][:6]))
        if len(d['slides']) > 6:
            slide_summary += f'... (+{len(d["slides"])-6})'
        variant_tag = f" [{d.get('variant', '?')}]" if 'variant' in d else ''
        lines.append(f"  [{i+1}] {d['start_s']:.1f}s – {d['end_s']:.1f}s "
                     f"({d['duration_s']:.1f}s, {d['cycles']} cycles){variant_tag}")
        lines.append(f"      Slides: {slide_summary}")

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python umiyuri_detector.py <maidata.txt> [difficulty]")
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

    detections = detect_umiyuri(notes)
    print(format_detections(detections, meta.title))

    score = umiyuri_score(notes)
    print(f"\nUmiyuri score: {score:.1%}")


if __name__ == '__main__':
    main()
