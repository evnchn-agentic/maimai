#!/usr/bin/env python3
"""
Simai chart parser and ASCII visualizer for maimai charts.

Parses maidata.txt files into time-stamped events, then renders them
as fixed-time-step ASCII representations for pattern analysis.
"""

import re
import sys
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Note:
    """A single note event at a specific time."""
    time_ms: float          # absolute time in milliseconds
    position: int           # button 1-8, or 0 for touch
    note_type: str          # 'tap', 'hold', 'slide', 'break', 'each'
    raw: str                # raw simai token
    hold_duration_ms: float = 0.0
    slide_shape: str = ''   # -, >, <, ^, p, q, s, z, v, V, w, pp, qq
    slide_end: int = 0      # end position for slides
    modifiers: str = ''     # b, x, etc.
    slide_duration_ms: float = 0.0  # how long the slide takes to travel
    bpm: float = 120.0              # BPM at time of this note (for slide delay calc)

    @property
    def slide_delay_ms(self) -> float:
        """The 1-beat delay before the slide star starts moving."""
        return 60000.0 / self.bpm  # 1 quarter note in ms

    @property
    def slide_action_ms(self) -> float:
        """When the slide action begins (star starts moving)."""
        if self.note_type != 'slide':
            return self.time_ms
        return self.time_ms + self.slide_delay_ms

    @property
    def slide_end_ms(self) -> float:
        """When the slide finishes (star arrives at endpoint).
        = tap time + 1 beat delay + travel duration."""
        if self.note_type != 'slide' or not self.slide_duration_ms:
            return self.time_ms + self.slide_delay_ms if self.note_type == 'slide' else self.time_ms
        return self.time_ms + self.slide_delay_ms + self.slide_duration_ms


@dataclass
class ChartMetadata:
    title: str = ''
    artist: str = ''
    bpm: float = 120.0
    designer: str = ''
    level: str = ''
    genre: str = ''
    cabinet: str = ''
    version: str = ''


@dataclass
class ParsedChart:
    metadata: ChartMetadata = field(default_factory=ChartMetadata)
    notes: list = field(default_factory=list)
    duration_ms: float = 0.0


def parse_maidata(filepath: str) -> dict:
    """Parse a maidata.txt file, returning metadata and raw chart strings."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {
        'metadata': ChartMetadata(),
        'charts': {}  # difficulty_num -> raw chart string
    }

    # Parse metadata
    for match in re.finditer(r'&(\w+)=(.+)', content):
        key, value = match.group(1), match.group(2).strip()
        if key == 'title':
            result['metadata'].title = value
        elif key == 'artist':
            result['metadata'].artist = value
        elif key == 'wholebpm':
            result['metadata'].bpm = float(value)
        elif key == 'genre':
            result['metadata'].genre = value
        elif key == 'cabinet':
            result['metadata'].cabinet = value
        elif key == 'version':
            result['metadata'].version = value

    # Extract chart data for each difficulty
    for match in re.finditer(r'&inote_(\d+)=\s*\n(.*?)(?=\n&|\Z)', content, re.DOTALL):
        diff_num = int(match.group(1))
        chart_str = match.group(2).strip()
        if chart_str:
            result['charts'][diff_num] = chart_str

    # Extract levels and designers
    for match in re.finditer(r'&lv_(\d+)=(.+)', content):
        diff_num = int(match.group(1))
        level = match.group(2).strip()
        if diff_num not in result:
            result[f'lv_{diff_num}'] = level
    for match in re.finditer(r'&des_(\d+)=(.+)', content):
        diff_num = int(match.group(1))
        des = match.group(2).strip()
        result[f'des_{diff_num}'] = des

    return result


def parse_note_token(token: str) -> list:
    """Parse a single note token (may contain Each '/' separators).
    Returns list of (position, note_type, modifiers, slide_info, hold_info) tuples."""
    if not token or token == 'E':
        return []

    # Split by '/' for Each (simultaneous) notes
    parts = token.split('/')
    results = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Extract position (first digit)
        m = re.match(r'^(\d)', part)
        if not m:
            continue
        position = int(m.group(1))
        rest = part[1:]

        note_type = 'tap'
        modifiers = ''
        slide_shape = ''
        slide_end = 0
        hold_dur_str = ''

        # Check for modifiers at start (before slide/hold)
        while rest and rest[0] in 'bxf$@':
            modifiers += rest[0]
            rest = rest[1:]

        # Check for hold
        if rest.startswith('h'):
            note_type = 'hold'
            rest = rest[1:]
            # Extract duration
            hm = re.match(r'\[([^\]]+)\]', rest)
            if hm:
                hold_dur_str = hm.group(1)
                rest = rest[hm.end():]

        # Check for slide
        slide_dur_str = ''
        slide_match = re.match(r'([-><^pqszwvV]+)(\d)(\[([^\]]+)\])?', rest)
        if slide_match:
            note_type = 'slide'
            slide_shape = slide_match.group(1)
            slide_end = int(slide_match.group(2))
            if slide_match.group(4):
                slide_dur_str = slide_match.group(4)

        if 'b' in modifiers:
            if note_type == 'tap':
                note_type = 'break'

        results.append({
            'position': position,
            'note_type': note_type,
            'modifiers': modifiers,
            'slide_shape': slide_shape,
            'slide_end': slide_end,
            'hold_dur_str': hold_dur_str,
            'slide_dur_str': slide_dur_str,
            'raw': part,
        })

    return results


def calc_hold_duration_ms(dur_str: str, bpm: float) -> float:
    """Calculate hold duration in ms from simai duration string."""
    if not dur_str:
        return 0.0
    # Absolute time: #seconds
    if dur_str.startswith('#'):
        return float(dur_str[1:]) * 1000.0
    # Relative: divisor:count
    m = re.match(r'(\d+):(\d+)', dur_str)
    if m:
        divisor = int(m.group(1))
        count = int(m.group(2))
        beat_ms = 60000.0 / bpm
        return (4.0 / divisor) * count * beat_ms
    return 0.0


def parse_chart_string(chart_str: str, bpm: float) -> list:
    """Parse a raw chart string into a list of Note objects with absolute timestamps."""
    notes = []
    current_bpm = bpm
    current_division = 4  # default quarter notes
    current_time_ms = 0.0
    beat_ms = 60000.0 / current_bpm
    tick_ms = (4.0 / current_division) * beat_ms  # ms per comma

    # Remove comments
    chart_str = re.sub(r'\|\|.*', '', chart_str)
    # Remove newlines, collapse whitespace
    chart_str = chart_str.replace('\n', '').replace('\r', '')

    i = 0
    while i < len(chart_str):
        c = chart_str[i]

        # BPM change
        if c == '(':
            end = chart_str.index(')', i)
            current_bpm = float(chart_str[i+1:end])
            beat_ms = 60000.0 / current_bpm
            tick_ms = (4.0 / current_division) * beat_ms
            i = end + 1
            continue

        # Division change
        if c == '{':
            end = chart_str.index('}', i)
            div_str = chart_str[i+1:end]
            if div_str.startswith('#'):
                # Absolute timing mode
                tick_ms = float(div_str[1:]) * 1000.0
            else:
                current_division = int(div_str)
                tick_ms = (4.0 / current_division) * beat_ms
            i = end + 1
            continue

        # Comma = advance time
        if c == ',':
            current_time_ms += tick_ms
            i += 1
            continue

        # End marker — 'E' NOT followed by a digit (which would be a touch note like E4)
        if c == 'E' and (i + 1 >= len(chart_str) or not chart_str[i + 1].isdigit()):
            break

        # Touch notes (A, B, C, D, E followed by digit) — skip for now
        if c in 'ABCDE' and i + 1 < len(chart_str) and chart_str[i + 1].isdigit():
            # Skip touch note token (e.g., A4, E4f, C1h[...])
            j = i + 2  # past letter + digit
            while j < len(chart_str) and chart_str[j] not in ',({' and chart_str[j] != 'E':
                if chart_str[j] == '[':
                    while j < len(chart_str) and chart_str[j] != ']':
                        j += 1
                    j += 1
                else:
                    j += 1
            i = j
            continue
        # Center touch 'C' without digit
        if c == 'C' and (i + 1 >= len(chart_str) or chart_str[i + 1] in ',({' or not chart_str[i + 1].isdigit()):
            i += 1
            continue

        # Skip whitespace
        if c in ' \t':
            i += 1
            continue

        # Collect a note token (everything until next , or E or { or ()
        token_end = i
        bracket_depth = 0
        while token_end < len(chart_str):
            ch = chart_str[token_end]
            if ch == '[':
                bracket_depth += 1
            elif ch == ']':
                bracket_depth -= 1
            elif ch in ',E' and bracket_depth == 0:
                break
            elif ch in '({' and bracket_depth == 0:
                break
            token_end += 1

        token = chart_str[i:token_end].strip()
        if token:
            parsed = parse_note_token(token)
            for p in parsed:
                hold_ms = calc_hold_duration_ms(p['hold_dur_str'], current_bpm)
                slide_ms = calc_hold_duration_ms(p.get('slide_dur_str', ''), current_bpm)
                note = Note(
                    time_ms=current_time_ms,
                    position=p['position'],
                    note_type=p['note_type'],
                    raw=p['raw'],
                    hold_duration_ms=hold_ms,
                    slide_shape=p['slide_shape'],
                    slide_end=p['slide_end'],
                    modifiers=p['modifiers'],
                    slide_duration_ms=slide_ms,
                    bpm=current_bpm,
                )
                notes.append(note)

        i = token_end

    return notes


# ─── ASCII Visualizer ───

NOTE_CHARS = {
    'tap': 'o',
    'hold': '=',
    'slide': '~',
    'break': '*',
}

def render_ascii(notes: list, resolution_ms: float = 50.0, max_time_ms: float = None) -> str:
    """Render notes as a time-series ASCII chart.

    Each row = one time step (resolution_ms).
    Columns = positions 1-8 around the circle.

    Legend:
      o = tap
      = = hold (start)
      ~ = slide (start, with arrow showing direction)
      * = break
      . = empty
    """
    if not notes:
        return "(empty chart)"

    if max_time_ms is None:
        max_time_ms = max(n.time_ms for n in notes) + 500

    num_rows = int(max_time_ms / resolution_ms) + 1

    # Build grid: rows x 8 columns
    grid = [['.' for _ in range(8)] for _ in range(num_rows)]
    slide_annotations = {}  # row -> annotation string

    for note in notes:
        row = int(note.time_ms / resolution_ms)
        if row >= num_rows:
            continue
        col = note.position - 1  # 0-indexed
        if 0 <= col < 8:
            char = NOTE_CHARS.get(note.note_type, '?')
            # Don't overwrite more interesting notes with taps
            if grid[row][col] == '.' or char != 'o':
                grid[row][col] = char

            if note.slide_shape:
                slide_annotations[row] = slide_annotations.get(row, '') + \
                    f' [{note.position}{note.slide_shape}{note.slide_end}]'

    # Render
    lines = []
    lines.append(f"{'Time':>8s}  {'1':>2s} {'2':>2s} {'3':>2s} {'4':>2s} {'5':>2s} {'6':>2s} {'7':>2s} {'8':>2s}  Notes")
    lines.append('-' * 60)

    # Only show rows that have notes (or are near notes)
    active_rows = set()
    for note in notes:
        row = int(note.time_ms / resolution_ms)
        for r in range(max(0, row - 1), min(num_rows, row + 2)):
            active_rows.add(r)

    prev_row = -2
    for row in sorted(active_rows):
        if row >= num_rows:
            break
        if row > prev_row + 1 and prev_row >= 0:
            lines.append(f"{'...':>8s}")

        time_s = (row * resolution_ms) / 1000.0
        cols = ' '.join(f'{grid[row][c]:>2s}' for c in range(8))
        annotation = slide_annotations.get(row, '')

        # Count notes in this row
        note_count = sum(1 for c in range(8) if grid[row][c] != '.')
        density_bar = '|' * note_count if note_count > 0 else ''

        lines.append(f"{time_s:7.2f}s  {cols}  {density_bar}{annotation}")
        prev_row = row

    return '\n'.join(lines)


def render_density_profile(notes: list, bucket_ms: float = 1000.0) -> str:
    """Render a note density profile (notes per second)."""
    if not notes:
        return "(empty)"

    max_time = max(n.time_ms for n in notes)
    num_buckets = int(max_time / bucket_ms) + 1
    buckets = [0] * num_buckets

    for note in notes:
        bucket = int(note.time_ms / bucket_ms)
        if bucket < num_buckets:
            buckets[bucket] += 1

    max_density = max(buckets) if buckets else 1
    lines = []
    lines.append(f"Note density (per {bucket_ms/1000:.1f}s bucket, max={max_density}):")
    lines.append('')

    for i, count in enumerate(buckets):
        time_s = i * bucket_ms / 1000.0
        bar_len = int((count / max(max_density, 1)) * 50)
        bar = '█' * bar_len
        lines.append(f"{time_s:6.1f}s [{count:3d}] {bar}")

    return '\n'.join(lines)


def render_pattern_summary(notes: list) -> str:
    """Summarize note types, positions, and patterns."""
    if not notes:
        return "(empty)"

    type_counts = {}
    pos_counts = [0] * 8
    slide_shapes = {}

    for note in notes:
        type_counts[note.note_type] = type_counts.get(note.note_type, 0) + 1
        if 1 <= note.position <= 8:
            pos_counts[note.position - 1] += 1
        if note.slide_shape:
            slide_shapes[note.slide_shape] = slide_shapes.get(note.slide_shape, 0) + 1

    lines = []
    lines.append(f"Total notes: {len(notes)}")
    lines.append(f"Duration: {max(n.time_ms for n in notes) / 1000:.1f}s")
    lines.append(f"Avg density: {len(notes) / (max(n.time_ms for n in notes) / 1000):.1f} notes/sec")
    lines.append('')
    lines.append("Note types:")
    for ntype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  {ntype:>8s}: {count:4d} ({100*count/len(notes):.1f}%)")

    lines.append('')
    lines.append("Position distribution:")
    max_pos = max(pos_counts) if pos_counts else 1
    for i, count in enumerate(pos_counts):
        bar = '█' * int((count / max(max_pos, 1)) * 30)
        lines.append(f"  Btn {i+1}: {count:4d} {bar}")

    if slide_shapes:
        lines.append('')
        lines.append("Slide shapes:")
        for shape, count in sorted(slide_shapes.items(), key=lambda x: -x[1]):
            lines.append(f"  '{shape}': {count}")

    return '\n'.join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python simai_parser.py <maidata.txt> [difficulty_num] [--density] [--summary] [--ascii]")
        print("  difficulty_num: 2=Basic, 3=Advanced, 4=Expert, 5=Master, 6=Re:Master")
        print("  --density: show density profile")
        print("  --summary: show pattern summary")
        print("  --ascii: show ASCII timeline (default)")
        sys.exit(1)

    filepath = sys.argv[1]
    diff_num = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None

    flags = set(sys.argv[2:])
    show_density = '--density' in flags
    show_summary = '--summary' in flags
    show_ascii = '--ascii' in flags or (not show_density and not show_summary)

    data = parse_maidata(filepath)
    meta = data['metadata']
    print(f"Title: {meta.title}")
    print(f"Artist: {meta.artist}")
    print(f"BPM: {meta.bpm}")
    print(f"Available difficulties: {sorted(data['charts'].keys())}")
    print()

    if diff_num is None:
        # Pick highest available
        diff_num = max(data['charts'].keys())
        print(f"Auto-selecting difficulty {diff_num}")

    if diff_num not in data['charts']:
        print(f"Difficulty {diff_num} not found. Available: {sorted(data['charts'].keys())}")
        sys.exit(1)

    level = data.get(f'lv_{diff_num}', '?')
    designer = data.get(f'des_{diff_num}', '?')
    print(f"Difficulty {diff_num} (Lv.{level}, charter: {designer})")
    print()

    notes = parse_chart_string(data['charts'][diff_num], meta.bpm)

    if show_summary:
        print(render_pattern_summary(notes))
        print()

    if show_density:
        print(render_density_profile(notes))
        print()

    if show_ascii:
        print(render_ascii(notes, resolution_ms=100.0))


if __name__ == '__main__':
    main()
