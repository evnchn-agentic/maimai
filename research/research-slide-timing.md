# maimai Slide Timing Mechanics

## The 1-Beat Delay Rule

When a star note (slide start) is tapped, the slide does NOT begin moving immediately. There is a **1 quarter note (1 beat)** delay before the star starts traveling.

```
T=0:              Star tap (player hits the star note)
T + 1 beat:       Slide action begins (star starts moving along path)
T + 1 beat + dur: Slide ends (star arrives at endpoint)
```

The delay is BPM-dependent:
- 120 BPM → 500ms delay
- 150 BPM → 400ms delay
- 180 BPM → 333ms delay
- 210 BPM → 286ms delay

## Simai Format

Default: 1 beat delay (implicit, not written in the chart).

Override syntax:
- `[T#X:Y]` — single `#`. T is a BPM used to compute delay as `60/T` seconds. X:Y is slide travel duration.
- `[D##X:Y]` — double `##`. D is explicit delay in seconds.

In SimaiSharp: default delay = `SecondsPerBeat` = `60.0 / tempo`.

## Implications for Pattern Detection

### Umiyuri Pattern
In the each(tap+slide) groups:
- The **tap** resolves the PREVIOUS slide's endpoint arrival (1 beat has elapsed)
- The **slide star** is a NEW slide that will wait 1 beat before moving
- The interlocking cycle works because of this built-in delay

### 拍滑 (Tap+Slide)
When properly accounting for the delay, the slide's **action** (not its star tap) coincides with a regular tap — "one hand taps, one hand slides" simultaneously. The star tap is earlier; the physical slide motion is what aligns with the tap.

### 一筆畫 (One-Stroke)
Chained slides need the previous slide to finish before the next one's action begins. The 1-beat delay means each slide in the chain has a natural pause point.

## Sources
- SimaiSharp `SlideReader.cs` line 21 — default delay = `SecondsPerBeat`
- MaiLib README — "wait time of 1 beat or one 1/4 note"
- [donmai blog](https://listed.to/@donmai/18173/the-four-chart-formats-of-maimai-classic)
- [How MaiMai DX Judges Slides](https://listed.to/@donmai/44545/how-maimai-dx-judges-slides)
- [Delayed Slide blog](http://introductiontomaimai.blogspot.com/2017/02/delayed-slide.html)
