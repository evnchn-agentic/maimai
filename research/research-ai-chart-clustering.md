# AI/ML Approaches for Clustering Rhythm Game Charts by Archetype/Style

## 1. Feature Vector Representation

Charts can be encoded as feature vectors using pattern-derived attributes:

- **Note density** — actions per second, bucketed into levels 0–9
- **Pattern type frequencies** — streams, jumpstreams, handstreams, jacks
- **Time interval distributions** — 8-bit one-hot encoding of inter-note gaps
- **Action type vectors** — 4-bit one-hot per channel
- **Slide/hold complexity metrics**
- **Audio-side features** — multi-timescale STFT (23ms, 46ms, 93ms windows) as spectrograms

The [Predicting Chart Difficulty](https://link.springer.com/chapter/10.1007/978-981-33-4069-5_17) paper specifically extracts chart-pattern-derived attributes for classification.

## 2. Clustering Algorithms

- **DBSCAN + UMAP** — recommended for chart data since archetypes form irregular, non-spherical clusters. [UMAP docs](https://umap-learn.readthedocs.io/en/latest/clustering.html) describe manifold-aware dimensionality reduction before density-based clustering.
- **Hierarchical clustering** — suits comparing musical segments by melodic/rhythmic similarity.
- **K-means** — works for initial exploration but assumes spherical clusters.
- **Network-based** — model charts as graphs (nodes = notes/chords) and cluster via [complex network metrics](https://arxiv.org/pdf/1709.05193).

## 3. Dimensionality Reduction and Visualization

- **UMAP** — preserves global structure better than t-SNE, scales to large beatmap datasets. Ideal for exploring chart archetype landscapes.
- **t-SNE** — excels at revealing local clusters (e.g., tight groupings of stream-heavy vs. tech-heavy charts).
- See [Audio Explorer](https://pair-code.github.io/understanding-umap/) for UMAP embedding audio samples into 2D — directly analogous to chart embedding.

## 4. Charter Style Fingerprinting

No published work specifically targets beatmap author identification, but **authorship attribution via stylometry** is well-established in NLP. The analogous approach:

1. Extract charter-specific features (preferred pattern vocabulary, spacing tendencies, density curves, note placement biases) as a stylometric profile
2. Classify using character n-gram-like techniques adapted to note sequences

This is a viable but **unexplored research gap**.

## 5. Difficulty Estimation

The most-studied area in rhythm game ML:

- [PCG of Rhythm Games Using Deep Learning](https://link.springer.com/chapter/10.1007/978-3-030-34644-7_11) — LSTM networks with 7-component feature vectors (density + timing + action history)
- [osu-ml-difficulty](https://github.com/joseph-ireland/osu-ml-difficulty) — linear regression on replay hit-error data
- [Machine Translation Between Difficulties](https://ojs.aaai.org/index.php/AIIDE/article/download/12396/12255/15924) — treats difficulty conversion as a sequence-to-sequence problem

## 6. Related Chart Generation/Analysis Work

- [TaikoNation](https://dl.acm.org/doi/10.1145/3472538.3472589) — patterning quality in generated charts
- [Mug-Diffusion](https://github.com/Keytoyze/Mug-Diffusion) — modified Stable Diffusion for controllable chart generation
- [BeatLearning](https://github.com/sedthh/BeatLearning) — open-source generative models

**Key gap: clustering charts by archetype/style remains largely unexplored** — most work focuses on generation or difficulty, not taxonomic analysis.

## Sources

- [Predicting Chart Difficulty in Rhythm Games](https://link.springer.com/chapter/10.1007/978-981-33-4069-5_17)
- [TaikoNation](https://dl.acm.org/doi/10.1145/3472538.3472589)
- [PCG of Rhythm Games Using Deep Learning](https://link.springer.com/chapter/10.1007/978-3-030-34644-7_11)
- [Mug-Diffusion (GitHub)](https://github.com/Keytoyze/Mug-Diffusion)
- [BeatLearning (GitHub)](https://github.com/sedthh/BeatLearning)
- [osu-ml-difficulty (GitHub)](https://github.com/joseph-ireland/osu-ml-difficulty)
- [Machine Translation Between Difficulties (AAAI)](https://ojs.aaai.org/index.php/AIIDE/article/download/12396/12255/15924)
- [UMAP Clustering Documentation](https://umap-learn.readthedocs.io/en/latest/clustering.html)
- [Clustering Musical Pieces via Complex Networks](https://arxiv.org/pdf/1709.05193)
