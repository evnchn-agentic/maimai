# Simai Chart Format Specification

Simai is a text-based chart notation for maimai, stored in `maidata.txt` files. It is used by community tools including **SimAI**, **AstroDX**, **MajdataPlay/MajdataEdit**, **SimaiSharp**, and **MaiConverter**. The canonical documentation lives at `https://w.atwiki.jp/simai/pages/25.html` (Japanese wiki).

> **Note**: There is no formal "simai v1 vs v2" distinction. The format evolved incrementally — touch notes, ex notes, and fireworks were added for maimai DX. "simai2" is sometimes used informally for the DX-era extensions, but the format is generally just called "simai."

## File Structure

The file uses `&key=value` metadata pairs:

```
&title=Song Name
&artist=Artist Name
&des=Charter Name
&first=0.5
&lv_1=5
&lv_4=12+
&inote_1=(BPM){divisor}chart data here
&inote_4=(BPM){divisor}chart data here
```

Keys:
- `&title`, `&artist`, `&des` (designer)
- `&first` — audio offset in seconds
- `&lv_N` — difficulty level for chart N (1–7 maps to Easy/Basic/Advanced/Expert/Master/Re:Master/Utage)
- `&inote_N` — chart data for difficulty N

## Core Syntax

**BPM**: `(120)` sets BPM to 120. Can appear mid-chart for BPM changes.

**Measure division**: `{4}` = quarter notes, `{8}` = eighth notes, `{16}` = sixteenth notes. `{#2.0}` uses absolute timing in seconds.

**Tick separator**: `,` advances time by one subdivision. Multiple commas `,,` skip beats.

**End mark**: `E` marks end of chart.

**Comments**: `||` starts a comment until end of line.

A chart always starts with BPM and divisor: `(170){4}`.

## Note Types

### Tap
Button position `1`–`8` (clockwise from top):
```
(120){4}1,3,5,7,    || taps on buttons 1,3,5,7 with a rest
```

### Hold
Position + `h` + optional duration `[duration]`:
```
1h[4:1],    || hold on button 1 for 1 quarter note
2h[8:3],    || hold on button 2 for 3 eighth notes
3h[#1.5],   || hold for 1.5 seconds (explicit)
```
Duration format: `X:Y` = Y notes of X-subdivision (e.g., `4:1` = 1 quarter note). `#N` = N seconds explicit.

### Break
Append `b` modifier: `1b,` = break tap. `1bh[4:1],` = break hold.

### Ex Note
Append `x`: `1x,` = ex tap. `1bx,` = break ex tap.

### Star Note
`$` forces star appearance, `$$` forces spinning star. `@` forces normal (non-star) appearance. (`$` is stateful: first `$` = ForceStar, second `$` = ForceStarSpinning.)

### Mine Note
Append `m`: notes the player must avoid hitting. (Community/tool extension recognized by SimaiSharp.)

### Fake/Empty Note
`0` is a placeholder note.

### Complete Note Modifier Table (verified from SimaiSharp source)

| Modifier | Effect |
|----------|--------|
| `b` | Break note (higher grading value); on slides, marks the slide path as break |
| `x` | EX note style |
| `h` | Hold (needs duration `[...]`) |
| `f` | Fireworks effect (typically for touch notes) |
| `m` | Mine note (must avoid) |
| `?` | ForceInvalidate + FadeIn slide morph |
| `!` | ForceInvalidate + SuddenIn slide morph |
| `@` | ForceNormal appearance (non-star) |
| `$` | ForceStar; `$$` = ForceStarSpinning |

## Simultaneous Notes (Each)

`/` separates notes at the same time:
```
1/5,    || tap 1 and 5 simultaneously
1/3/5,  || tap 1, 3, and 5 simultaneously
```

**Pseudo-each** (backtick `` ` ``): Per SimaiSharp source, backtick is registered as an `EachDivider` token identical to `/` — both mean simultaneous. The "slight stagger" behavior is renderer-specific, not part of the format spec:
```
1`3`5,  || simultaneous (functionally identical to 1/3/5)
```

Adjacent digits without separators also denote simultaneous taps: `13` = tap 1 and 3 together.

## Slide Notation

Slides: start position + shape code + end position + duration:
```
1-5[4:1],   || straight slide from 1 to 5, duration 1 quarter note
```

### Slide Shape Codes (verified complete from SimaiSharp source)

| Code | Internal Type | Description |
|------|---------------|-------------|
| `-`  | StraightLine | Straight line between two buttons |
| `>`  | RingCw/Ccw | Along judgement ring, CW bias |
| `<`  | RingCw/Ccw | Along judgement ring, CCW bias |
| `^`  | RingCw/Ccw | Along judgement ring, shortest arc auto-selected |
| `p`  | CurveCcw | Arc counter-clockwise around center |
| `pp` | EdgeCurveCcw | Start to center (straight), then CCW arc to end |
| `q`  | CurveCw | Arc clockwise around center |
| `qq` | EdgeCurveCw | Start to center (straight), then CW arc to end |
| `s`  | ZigZagS | S-shaped zigzag |
| `z`  | ZigZagZ | Z-shaped zigzag |
| `v`  | Fold | Start to center (straight), center to end (straight) |
| `V`  | EdgeFold | Start to intermediate point (straight), then to end (straight) |
| `w`  | Fan | Fan pattern (always fans to opposite button) |

**This table is confirmed complete — no additional slide shapes exist beyond these 13 codes.**

### Slide Duration
`[BPM#X:Y]` where BPM overrides tempo for duration calc. `[D##X:Y]` sets explicit delay before slide starts. First part before `#` = slide intro delay; after `#` = travel duration.

### Chained Slides
Chain directly: `1-3-5[4:1],` slides from 1 → 3 → 5.

### Sibling Slides
Multiple slides from same star using `*`: `1-5*>3[4:1],` = straight slide to 5 AND arc slide to 3 from button 1.

### Slide Modifiers
- `?` — fade-in morph (suppress tap judgment on star head)
- `!` — sudden-in morph (suppress tap judgment on star head)

## Touch Notes (DX Cabinet)

Touch positions use sensor regions `A`, `B`, `D`, `E` (areas 1–8) and `C` (center, with optional `C1`/`C2`):
```
A1,        || touch at A-sensor position 1
C,         || touch at center
E5f,       || touch at E5 with fireworks effect
C1h[4:1],  || touch hold at center for 1 quarter note
```
Modifier `f` = fireworks effect. Touch holds use `h` + duration like regular holds.

## HiSpeed Changes

`HS*N>` mid-chart changes scroll speed multiplier (supported by MajdataEdit).

## Edge Cases and Quirks

- `^` auto-determines CW vs CCW by shortest arc. If start and end are 180° apart, behavior may be ambiguous.
- `V` (EdgeFold) crashes the game when start and end positions are the same.
- Straight slides (`-`) require at least two positions of separation; otherwise default to two places CCW.
- Zigzag patterns (`s`, `z`) have restricted valid end positions.
- `b` on a slide decorates the slide path, not the tap note.

## Sources

- [SimaiSharp Tokenizer.cs](https://github.com/reflektone-games/SimaiSharp/blob/main/SimaiSharp/src/Internal/LexicalAnalysis/Tokenizer.cs)
- [SimaiSharp NoteReader.cs](https://github.com/reflektone-games/SimaiSharp/blob/main/SimaiSharp/src/Internal/SyntacticAnalysis/States/NoteReader.cs)
- [SimaiSharp SlideReader.cs](https://github.com/reflektone-games/SimaiSharp/blob/main/SimaiSharp/src/Internal/SyntacticAnalysis/States/SlideReader.cs)
- [The Four Chart Formats of Maimai Classic](https://listed.to/@donmai/18173/the-four-chart-formats-of-maimai-classic)
- [MaiConverter how_to_make_charts.md](https://github.com/donmai-me/MaiConverter/blob/master/how_to_make_charts.md)
- [Simai wiki (canonical spec)](https://w.atwiki.jp/simai/pages/25.html)

## Key Repos

- **SimaiSharp** (`reflektone-games/SimaiSharp`) — C# parser/serializer, used by AstroDX
- **MaiConverter** (`donmai-me/MaiConverter`) — Python converter between simai/ma2/sdt
- **MajdataEdit/MajdataPlay** (`LingFeng-bbben`) — Chart editor and player
- **tree-sitter-simai** (`donmai-me/tree-sitter-simai`) — Formal grammar definition
