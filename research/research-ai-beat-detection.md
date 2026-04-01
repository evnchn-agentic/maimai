# Audio Analysis for maimai Chart Creation

## 1. Beat/Onset Detection Libraries

### Madmom (recommended for beat tracking)
Genre-specific RNNs, consistently highest alignment with annotated beat positions. Excels with complex rhythms and electronic music — directly relevant to maimai's J-pop/electronic soundtrack. `DBNBeatTrackingProcessor` is state-of-the-art for beat/downbeat tracking.

### Librosa (recommended for feature extraction)
Most accessible library. Best for prototyping and feature extraction (MFCCs, chroma, spectral features). Known issue: detected beats tend to arrive slightly before actual onsets. Not ideal for production beat tracking.

### Essentia
`RhythmExtractor2013` with two modes: slower multi-feature (more accurate) and faster `degara` mode. Good for tempo estimation.

### Aubio
Lightweight C library with Python bindings. Good for real-time onset detection.

**Recommendation:** Madmom for beat/downbeat tracking, librosa for spectral feature extraction (mel spectrograms, onset strength envelopes).

## 2. Audio Features for Chart Generation

| Feature | Use Case |
|---|---|
| **Onset detection** | Note attack timing — foundation of note placement |
| **Beat/downbeat tracking** | Establishes metrical grid |
| **Spectral flux** | Energy changes across frequency bands, intensity shifts |
| **Musical structure segmentation** | Intro/verse/chorus/bridge — critical for difficulty pacing |
| **Source separation** | Per-instrument onset detection (drums→taps, vocals→slides) |

### Musical Structure Analysis
- **All-in-One Music Structure Analyzer** ([mir-aidj/all-in-one](https://github.com/mir-aidj/all-in-one)) — detects intro/verse/chorus/bridge
- **MSAF** ([urinieto/msaf](https://github.com/urinieto/msaf)) — Music Structure Analysis Framework

## 3. How Existing Pipelines Process Audio

### Mapperatorinator (SOTA, 219M params)
- **Whisper-based** transformer encoder-decoder
- Mel spectrogram: **n_mels=388, hop_length=128, sample_rate=16000, n_fft=1024, f_max=8000** via nnAudio
- Time quantized to **10ms intervals**
- Conditioned on gamemode, difficulty, mapper style, year
- Diffusion refinement step for coordinate denoising

### osuT5
- Mel spectrogram frames as encoder input, sparse event-based output
- Inspired by Google Magenta's MT3
- Requires externally provided BPM/offset

### osu-dreamer
- Diffusion process from raw audio
- Spectrogram-based input

**Key takeaway:** All major pipelines use **mel spectrograms**, not CQT or raw STFT. None rely on explicit beat tracking — neural networks learn rhythmic structure implicitly from spectrograms.

## 4. maimai-Specific Considerations

- **BPM range:** ~100–290 BPM, bulk in 130–200 range (J-pop, Vocaloid, electronic)
- **Chart timing:** Classic maimai uses measure number with 4–6 decimal places of precision, BPM stored separately
- **Slide timing:** Slide notes have a tap judgment + delay (typically quarter note) before star moves — placement must account for beat structure
- **Musical phrasing:** Charts follow 4-bar and 8-bar phrase structures. Difficulty increases at chorus, eases at verse/bridge
- **Note type mapping:** TAP→drums, HOLD→sustained notes, SLIDE→melodic runs, BREAK→climactic moments

## 5. Source Separation

### Demucs v4 (Hybrid Transformer) — SOTA
Separates into drums/bass/vocals/other. Operates on both spectrogram and waveform domains with cross-attention.

### Spleeter
Faster but lower quality.

### Application to maimai
Running onset detection separately on isolated stems enables mapping different instruments to different note types:
- Drum onsets → TAPs
- Vocal phrases → SLIDEs
- Bass hits → BREAKs
- Sustained melodies → HOLDs

## Sources

- [Mapperatorinator](https://github.com/OliBomby/Mapperatorinator)
- [osuT5](https://github.com/gyataro/osuT5)
- [osu-dreamer](https://github.com/jaswon/osu-dreamer)
- [Beat detection model comparison (BIFF.ai)](https://biff.ai/a-rundown-of-open-source-beat-detection-models/)
- [All-in-One Music Structure Analyzer](https://github.com/mir-aidj/all-in-one)
- [MSAF](https://github.com/urinieto/msaf)
- [Demucs](https://github.com/facebookresearch/demucs)
- [Essentia beat detection tutorial](https://essentia.upf.edu/tutorial_rhythm_beatdetection.html)
- [maimai chart formats](https://listed.to/@donmai/18173/the-four-chart-formats-of-maimai-classic)
- [Osu2MIR beat tracking dataset](https://arxiv.org/abs/2509.12667)
