<img src="hero.png" width="280" align="right" alt="evnchn playing maimai DX arcade cabinet" />

# maimai

**AI-powered chart analysis, pattern detection, chart generation, and player recommendation for maimai — all planned to be built through agentic coding with Claude Code.**

> Being built through agentic coding with [Claude Code](https://claude.ai/claude-code). The AI researches, codes, iterates, and ships — while the human validates by reviewing gameplay captures and testing on a simulator.

---

## What is maimai?

[maimai](https://maimai.sega.jp/) is a SEGA arcade rhythm game with a circular screen surrounded by 8 touch-sensitive buttons. Players tap, hold, and slide along the screen in time with music. Unlike lane-based rhythm games, maimai's 360-degree layout enables unique spatial patterns — including techniques where both hands must operate independently, creating some of the hardest coordination challenges in any rhythm game.

This project applies AI to understand, detect, and eventually generate these patterns.

## Vision

Three streams of work, all building on each other:

### Stream 1: Beat Detection
Extract maimai-relevant beats from audio — not just generic onset detection, but rhythmic structures that map well to tap/slide/hold patterns.

### Stream 2: Chart Generation
1. **Pattern Detection** — identify named chart patterns (Umiyuri, 拍滑, 一筆畫, etc.) from parsed chart data
2. **Pattern Understanding** — reverse-engineer what defines each pattern structurally
3. **Pattern Slotting** — place understood patterns onto detected beats to generate new charts

### Stream 3: Player Analysis
Correlate player scores with chart pattern profiles to recommend charts for rating improvement (play to strengths) or skill development (target weaknesses).

## What's Shipped

### [Umiyuri Detector](umiyuri/)

The first completed deliverable. A structural detector for the ウミユリ (海底譚) chart pattern — one of the most feared techniques in maimai, requiring true hand independence.

- **97% accuracy** on 31 ground truth samples (20 TPs, 11 TNs)
- Detects **classic** and **fragrance-type** variants
- Built through **6+ hours of agentic TDD** — the AI proposed rules, ran against the DB, the human reviewed gameplay captures, reported false positives, and the AI fixed them
- NiceGUI web dashboard with leaderboard and mai-notes.com integration

See [umiyuri/](umiyuri/) for the full story.

## Future Work

- **拍滑 detector** — the foundational tap+slide pattern (related to but distinct from Umiyuri)
- **一筆畫 detector** — one-stroke connected slide patterns
- **Audio-to-chart pipeline** — beat detection → pattern slotting → simai output
- **Player recommendations** — "play X to improve your Umiyuri" / "play Y for easy rating"
- **Chart generation v2** — data-driven, learning from the corpus

## License

MIT
