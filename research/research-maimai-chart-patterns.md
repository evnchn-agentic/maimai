# maimai Chart Design Patterns

## Core Layout

maimai uses 8 buttons arranged in a circle (positions 1–8, like a clock) plus a touch screen center, enabling radial symmetry impossible in lane-based games like IIDX or SDVX.

## Fundamental Patterns

- **Streams**: Consecutive single taps moving around the ring — clockwise, counterclockwise, or alternating. At higher levels these become dense 16th-note streams requiring fluid hand movement around the panel.
- **Jacks**: Repeated hits on the same button position. Uncommon compared to lane-based games since maimai's circular layout favors movement, but used for accent/emphasis.
- **Trills**: Rapid alternation between two positions, typically opposite or adjacent buttons (e.g., 1-5 or 1-2). Cross-body trills (e.g., 3-7) force awkward hand crossings.
- **Cross-hands / Cross-body**: Patterns requiring one hand to reach past the other, exploiting the circular layout. A signature maimai challenge absent from flat-panel games.
- **Each (Both-hand simultaneous)**: Two notes at the same timing on different positions, often mirror-symmetric (e.g., positions 2+6). "Each" patterns are a core maimai vocabulary term.

## Slide Patterns

Slides are maimai's most distinctive element — the player traces a path along the screen.

- **Straight slides**: Direct lines across the circle (e.g., 1 to 5).
- **Zig-zag / Wi-Fi slides**: Chained slides alternating direction, creating a "Wi-Fi antenna" visual. Community calls these "Wi-Fi slides."
- **Star patterns / Fan slides**: Multiple slides radiating from one origin point simultaneously, creating a star or fan shape.
- **Circle slides**: Slides tracing a full or partial arc around the ring. Full 360-degree circle slides are iconic high-difficulty tech.
- **S-curves and compound slides**: Slides that curve through intermediate points.

## Difficulty Progression

| Level | Characteristics |
|---|---|
| **Basic/Advanced** | Simple streams in one direction, basic holds, straight slides, minimal cross-hand. Patterns stay in comfortable "home" positions. |
| **Expert** | Introduction of cross-hand, faster streams, Each patterns, multi-directional slides, and basic touch notes. |
| **Master** | Dense streams with direction changes, complex slide layering (slides overlapping with taps), Wi-Fi slides, break notes in syncopated positions, heavy cross-body movement. |
| **Re:Master** | Everything at once — extreme density, reading difficulty through overlapping slide paths, "spinning" patterns requiring continuous circular hand motion, and patterns exploiting visual ambiguity. |

## Named Patterns (Song-Specific)

### ウミユリ配置 (Umiyuri Pattern) — from "ウミユリ海底譚" (Umiyuri Kaiteitan)

The most famous named pattern in maimai. Exploits the rule that **slides begin one beat after the star note is struck**:

1. Hit one side of an Each (イーチ) note containing a star — this queues a slide to begin one beat later
2. While waiting for that slide to activate, your other hand taps a separate note
3. When the next Each arrives, trace the previously queued slide with one hand while the other hand hits the new Each (queuing yet another slide)
4. The cycle repeats: "downbeats with one hand, offbeats with both hands"

First appears prominently around combo 301 in the original song's chart. Nearly unavoidable for players pushing past rainbow rating — broadened versions appear across many Level 13+ charts.

**Sources:** [note.com explanation](https://note.com/namea_chunibyo/n/n8c7bc59683ff), [TonevoAdventCalendar theory](https://tonevoadventcalendar.hatenablog.com/entry/2023/12/14/2)

### デスサイズ配置 (Death Scythe Pattern)

Named after the song "Death Scythe." Adjacent outer-ring taps executed while simultaneously managing slides.

### 魔法陣 (Magic Circle)

Center-crossing straight-line slides that gradually rotate point-symmetrically along diagonals.

### 一筆書き / 一筆畫 (Hitofude-gaki / One-Stroke Slide)

Multiple slides **connected without interruption**, traced as one continuous motion across the screen. The player hits a star note, then after the one-beat delay traces a long connected slide path that can span the entire diameter multiple times. Key to execution: maintaining consistent speed and beat awareness throughout.

**Source:** [Gamerch strategy guide](https://gamerch.com/maimai/534658)

## Named Patterns (Generic)

### From the "10 Famous Patterns" List ([kioblog source](https://gekkouga-kio.hatenablog.com/entry/2023/12/18/000144))

| Pattern | Japanese | Description |
|---|---|---|
| **Swing Rhythm** | ハネリズム | Jazz-like skip rhythm; grouped as "ta-tta" or "ta + tatta + ta" to avoid arm crossing |
| **Vertical Chain** | 縦連 | Rapid repeated taps on a single button position |
| **Mixed Phrase** | 混フレ (混合フレーズ) | Left and right hands execute different rhythmic patterns simultaneously |
| **Continuous Wrapping Slide** | 連続巻き込みスライド | Sequential slides with overlapping tap timing |
| **Rotation/Flow** | 回転・ながし | High-density adjacent taps requiring smooth sweeping arm motion |
| **Trill** | トリル | Rapid alternation between two positions |

### Other Named Patterns

- **8の字 (Hachi-no-ji / Figure-8)**: Slide patterns tracing a figure-8 shape across the screen.
- **蛇行 (Dakou / Meandering)**: Zigzag slide patterns that snake across the playfield.
- **タケノコ (Takenoko / Bamboo shoot)**: Patterns where notes "sprout" outward from center touch regions.

## Community Terminology and Techniques

### Chart Description Terms
- **配置 (Haichi)**: General term for note placement/arrangement.
- **認識難 (Ninshiki-nan)**: Patterns hard to visually parse, even if not physically difficult.
- **物量 (Butsuryou / "Volume")**: Charts defined by sheer note density rather than technical patterns.
- **初見殺し (Shoken-goroshi / "First-sight killer")**: Patterns designed to catch players off-guard on first play.
- **局所難 (Kyokusho-nan)**: Localized difficulty spikes within otherwise easier charts.
- **総合力 (Sougou-ryoku)**: Charts testing comprehensive/combined skills across multiple pattern types.
- **サビ落とし (Sabi-otoshi)**: Dropping difficulty at the musical climax for artistic effect.

### Player Techniques (from [Gamerch glossary](https://gamerch.com/maimai/533406))
- **餡蜜 (Anmitsu)**: Hitting staggered notes simultaneously despite timing mismatch — sacrifices accuracy for survivability.
- **逆餡蜜 (Gyaku-Anmitsu)**: Deliberately separating simultaneous notes into sequential hits.
- **出張 (Shutcho / "Business trip")**: Using the left hand on the right side or vice versa — an essential high-level skill.
- **巻き込み (Makikomi)**: Accidentally triggering adjacent note judgments while tracing slides.
- **無理押し (Murioshi)**: Physically impossible or near-impossible note configurations (banned in official charts except party mode).
- **洗濯機 (Sentakuki / "Washing machine")**: The nickname for the maimai cabinet itself, officially acknowledged by SEGA and Sharp.

## General Techniques and Community Terms

- **Spinning / Washing machine**: Continuous circular motion patterns forcing the player to "spin" their hands around the ring.
- **Wi-Fi**: Fan-shaped simultaneous slides resembling a Wi-Fi icon.
- **Touch mixups**: Center touch notes interleaved with ring taps, forcing rapid depth-of-field switching between rim and screen center.
- **Break placement**: Break notes (score-critical) placed at musical climaxes. Skilled charters place them where the pattern naturally guides the player's hand for satisfying "crits."
- **Endurance walls**: Sustained high-density sections testing stamina, common in Master/Re:Master.

## Sources

- [10 Famous Patterns (kioblog)](https://gekkouga-kio.hatenablog.com/entry/2023/12/18/000144)
- [Gamerch maimai glossary](https://gamerch.com/maimai/533406)
- [Gamerch maimai strategy guide](https://gamerch.com/maimai/534658)
- [Umiyuri pattern theory (TonevoAdventCalendar)](https://tonevoadventcalendar.hatenablog.com/entry/2023/12/14/2)
- [Umiyuri pattern explanation (note.com)](https://note.com/namea_chunibyo/n/n8c7bc59683ff)
- [SEGA official "washing machine" tweet](https://x.com/SEGA_OFFICIAL/status/1164107364191989760)

## What the Circular Layout Uniquely Enables

Mirror symmetry across any axis, true 360-degree movement patterns, variable-distance cross-hand (adjacent vs. opposite positions), and slides that would have no analog in a flat lane system. This makes maimai charting fundamentally **spatial rather than columnar**.
