# AI/ML Models for Rhythm Game Chart Generation

## 1. Key Projects and Papers

### Dance Dance Convolution (2017)
The foundational paper (Donahue, Lipton, McAuley — UCSD). Decomposes chart generation into step placement (when) and step selection (which), using CNNs + RNNs on audio spectrograms with a conditional LSTM for step selection. Trained on 350,000+ steps from StepMania. [Paper](https://www.researchgate.net/publication/315492559_Dance_Dance_Convolution)

### Mapperatorinator
State-of-the-art (219M param modified Whisper encoder-decoder transformer). Takes mel-spectrograms, outputs sparse event tokens. Supports all osu! gamemodes. Controls difficulty via metadata tokens (star rating, mapper style, year). Uses 90%-overlapping 8.2s windows for long-form generation. [GitHub](https://github.com/OliBomby/Mapperatorinator)

### MuG-Diffusion
Adapted from Stable Diffusion to incorporate audio waveforms. Currently supports 4K VSRG only but has **maimai listed on its roadmap**. Generates 4 charts for a 3-min song in ~30 seconds on a 3050Ti. [GitHub](https://github.com/Keytoyze/Mug-Diffusion)

### osu-dreamer
Diffusion-based model generating osu! maps from raw audio. [GitHub](https://github.com/jaswon/osu-dreamer)

### BeatLearning
Open-source transformer using a tokenized format (BEaRT) where each 100ms time slice encodes note events paired with mel spectrogram features. [GitHub](https://github.com/sedthh/BeatLearning)

### osumapper
Older TensorFlow-based automatic beatmap generator, one of the earliest deep learning approaches. [GitHub](https://github.com/kotritrona/osumapper)

### osuT5
Transformer encoder-decoder (T5 architecture) generating osu! beatmaps from spectrograms. [GitHub](https://github.com/gyataro/osuT5)

## 2. Best Generative Model Architectures

| Approach | Examples | Strengths |
|---|---|---|
| **Transformer (seq-to-seq)** | Mapperatorinator, BeatLearning, osuT5 | Best current results; handles long-range musical structure; controllable via conditioning tokens |
| **Diffusion** | osu-dreamer, MuG-Diffusion | High diversity; strong controllability (difficulty, pattern type, long-note ratio) |
| **CNN + RNN / LSTM** | Dance Dance Convolution, osumapper | Proven baseline; good at local audio-to-step alignment |
| **Rule-based** | ArrowVortex, StepCharter | Deterministic; useful for pattern conversion but limited musical awareness |

Transformers and diffusion models are currently dominant.

## 3. Audio-to-Chart Pipeline

```
Raw audio → Mel spectrogram / audio features → Encoder (audio understanding)
    → Decoder (note event generation) → Post-processing → Chart file
```

- Mapperatorinator quantizes audio at 10ms intervals, snaps positions to a 32-pixel grid
- MuG-Diffusion treats the chart as a 2D image-like representation and denoises it conditioned on audio
- All systems require a chart format serializer (e.g., .osu, .sm, Simai)

## 4. Maimai-Specific Challenges

- **Slide paths** require modeling continuous trajectories, not just discrete positions
- **Touch notes** occupy arbitrary screen positions
- **Circular geometry** means adjacency wraps around
- **No production-ready AI maimai chart generator exists yet**

### Available Resources for Maimai

- [maimai charts dataset (~1,394 charts in Simai format, ~5.4GB)](https://huggingface.co/datasets/rhythm-world/maimai-charts) on HuggingFace
- [MaiConverter](https://github.com/donmai-me/MaiConverter) — Python parsing for Simai/Ma2/SDT formats
- MuG-Diffusion lists maimai as a future target
- An experimental [ChatGPT-based maimai chart builder](https://chatgpt.com/g/g-hKm3qxCvG-maimai-chart-builder) exists as a GPT

## 5. Difficulty Control

Three approaches:
1. **Conditioning tokens** — Mapperatorinator prepends difficulty star rating as metadata
2. **Explicit parameters** — MuG-Diffusion accepts star rating or Etterna MSD values plus pattern-type controls
3. **Difficulty-aware training** — Dance Dance Convolution conditions its step placement CNN on chart difficulty level

## Key Takeaway for Maimai

The most viable path: (1) use the HuggingFace maimai dataset + MaiConverter for data preparation, (2) adapt a transformer (Mapperatorinator-style) or diffusion model (MuG-Diffusion-style) with tokenization for circular positions, slide paths, and touch notes, (3) condition on difficulty level during training.

## Sources

- [Dance Dance Convolution](https://www.researchgate.net/publication/315492559_Dance_Dance_Convolution)
- [Mapperatorinator](https://github.com/OliBomby/Mapperatorinator)
- [MuG-Diffusion](https://github.com/Keytoyze/Mug-Diffusion)
- [osu-dreamer](https://github.com/jaswon/osu-dreamer)
- [BeatLearning](https://github.com/sedthh/BeatLearning)
- [osumapper](https://github.com/kotritrona/osumapper)
- [osuT5](https://github.com/gyataro/osuT5)
- [maimai charts dataset (HuggingFace)](https://huggingface.co/datasets/rhythm-world/maimai-charts)
- [MaiConverter](https://github.com/donmai-me/MaiConverter)
- [AutoOsu (ISMIR 2023)](https://ismir2023program.ismir.net/lbd_319.html)
- [Difficulty classification via HMMs](https://link.springer.com/chapter/10.1007/978-3-031-47457-6_16)
