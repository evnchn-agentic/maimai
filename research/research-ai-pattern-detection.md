# AI/ML Models for Pattern Detection in Rhythm Game Charts

## 1. Supervised Pattern Detection: Best Architectures

### RNNs / LSTMs
The most proven architecture for rhythm game chart tasks. TaikoNation used a multi-layer LSTM to predict both note onsets and note patterning simultaneously, treating the chart as a temporal sequence. LSTMs handle variable-length, time-dependent charts naturally.

### Transformers
Gaining ground. BeatLearning uses a BERT/GPT-inspired tokenizer approach, treating chart elements as tokens. Scales better and generalizes across game formats and difficulty levels.

### CNNs
Excel at audio feature extraction (Mel spectrograms, STFTs) as a preprocessing frontend before temporal models. Also used for beat detection directly.

### Graph Neural Networks (GNNs)
Not yet applied to rhythm games but a strong theoretical fit for maimai specifically. Spatio-temporal GNNs (ST-GNNs) model data with both spatial structure and temporal evolution. Maimai's 8 buttons could be graph nodes with edges encoding adjacency around the circle, with note events as temporal signals.

## 2. Unsupervised / Feature-Mining Approaches

### Autoencoders (LSTM-AE, Convolutional AE, VAE)
Convolutional autoencoders can discover patterns in time series without labels. Latent vectors can be clustered (e.g., KMeans) to reveal recurring pattern types. Variational recurrent autoencoders learn structure with unsupervised training — suitable for discovering chart motifs.

### Similarity Embedding Networks
Siamese convolutional networks learn to embed sequential music fragments into a shared space, enabling unsupervised discovery of sequential patterns. This self-supervised approach (predicting whether fragments are consecutive and in order) could be adapted to chart subsequences.

### Sequential Pattern Mining
Algorithms like Seq2Pat extract frequent subsequences from sequential data. Combined with clustering, these can identify recurring chart motifs (e.g., spin patterns, zigzag across the circle) without human labeling.

## 3. Maimai-Specific Challenges

- **Circular topology:** Buttons 1 and 8 are adjacent, unlike linear lanes. Standard positional encodings break down; cyclic/angular encodings (sin/cos of button angle) or graph-based adjacency needed.
- **Multi-modal input:** Tap, Hold, Slide, Touch, Break each have different mechanics. Representation must encode note type, position, timing, and duration.
- **Rotational equivalence:** A pattern on buttons 1-2-3 is structurally identical to one on 5-6-7. Models should be rotation-equivariant or data should be augmented with rotations.

## 4. Relevant Academic Work

- **TaikoNation** (2021) — end-to-end LSTM pipeline for patterning-focused chart generation in Taiko.
- **PCG of Rhythm Games Using Deep Learning** (Springer, 2019) — LSTM-based DDR chart generation.
- **Musical difficulty estimation via hybrid deep learning** (ScienceDirect, 2022) — combining handcrafted features with deep learning, 10%+ improvement over single approaches.
- **Analysis of Algorithm Complexity in maimai DX** (ITB, 2023) — algorithmic analysis of maimai chart complexity using discrete mathematics.
- **Similarity Embedding Network for Unsupervised Sequential Pattern Learning** (2017) — self-supervised Siamese networks for music pattern discovery.

## 5. Practical Input Representation for Maimai

A maimai chart timestep could be encoded as a vector containing:

1. Binary/one-hot array over 8 buttons + touch zones indicating active notes
2. Note type flags (tap/hold/slide/break)
3. Angular position encoded as sin/cos pairs
4. Audio features (Mel spectrogram frame)
5. Temporal context (BPM, time since last note)

Stacking across time yields a multivariate time series suitable for 1D CNNs, LSTMs, or Transformers.

## Sources

- [TaikoNation](https://arxiv.org/pdf/2107.12506)
- [PCG of Rhythm Games Using Deep Learning](https://link.springer.com/chapter/10.1007/978-3-030-34644-7_11)
- [Musical Beat Detection with CNNs](http://tommymullaney.com/projects/rhythm-games-neural-networks)
- [Hybrid Deep Learning for Musical Difficulty Estimation](https://www.sciencedirect.com/science/article/pii/S1110016822002356)
- [Analysis of Algorithm Complexity in maimai DX](https://informatika.stei.itb.ac.id/~rinaldi.munir/Matdis/2023-2024/Makalah2023/Makalah-Matdis-2023%20(99).pdf)
- [Similarity Embedding Network](https://arxiv.org/abs/1709.04384v1)
- [Unsupervised Pattern Discovery in Time Series Using Autoencoders](https://link.springer.com/chapter/10.1007/978-3-319-49055-7_38)
- [Clustering Time Series via Autoencoder-based Deep Learning](https://arxiv.org/abs/2004.07296)
- [Spatio-Temporal GNNs](https://www.emergentmind.com/topics/spatio-temporal-graph-neural-network-st-gnn)
- [Time-based Chart Partitioning](https://ojs.aaai.org/index.php/AIIDE/article/download/36808/38946)
- [Seq2Pat](https://onlinelibrary.wiley.com/doi/full/10.1002/aaai.12081)
