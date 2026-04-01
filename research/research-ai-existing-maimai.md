# Existing AI/ML Projects for maimai

The maimai AI/ML landscape is **sparse**. The field is essentially wide open.

## 1. Academic Paper: Maimai Chart Generation

The only known academic paper directly targeting maimai: **"Maimai Chart Generation Model Based on Machine Learning Algorithms"** by Tianrun Lin (Beijing World Youth Academic), published March 2023 in *Applied and Computational Engineering*. Proposes a modular framework using LSTM, CNNs for audio feature extraction, and sequence-to-sequence learning. Theoretical/preliminary — no released implementation found.

- [ResearchGate](https://www.researchgate.net/publication/370031911_Maimai_Chart_Generation_Model_Based_on_Machine_Learning_Algorithms)
- [EWA Publishing](https://ace.ewapub.com/article/view/148)

## 2. HuggingFace Dataset: maimai-charts

~1,394 maimai charts in 3simai format (5.4 GB). Sourced from [Neskol/Maichart-Converts](https://github.com/Neskol/Maichart-Converts). Licensed ODC-BY, intended for research. The clearest foundation for future ML work.

- [rhythm-world/maimai-charts](https://huggingface.co/datasets/rhythm-world/maimai-charts)

## 3. MuG-Diffusion (Adjacent)

[Keytoyze/Mug-Diffusion](https://github.com/Keytoyze/Mug-Diffusion) — Stable Diffusion-based chart generation AI. Currently supports 4K VSRG only. **Maimai is listed as a future target** but not yet implemented.

## 4. Custom GPT: MAIMAI Chart Builder

An experimental ChatGPT custom GPT at [chatgpt.com/g/g-hKm3qxCvG-maimai-chart-builder](https://chatgpt.com/g/g-hKm3qxCvG-maimai-chart-builder). LLM wrapper, not a trained model — likely prompt-engineered to output simai notation.

## 5. Adjacent: Zhihu Neural Network Chart Generation

A [Zhihu article](https://zhuanlan.zhihu.com/p/107010304) describes using GRU networks to generate 4K Malody charts from MFCC audio features. Not maimai-specific but directly adjacent research from the Chinese community.

## 6. Diving-Fish's Tools

[Diving-Fish/maimaidx-prober](https://github.com/Diving-Fish/maimaidx-prober) — score tracker/query tool (查分器). **No ML features** — proxy-based data scraping and display.

## 7. AstroDX / MajdataPlay

No AI or ML features found. Pure simulators/players focused on rendering and gameplay.

## 8. Computer Vision / Auto-play

**No dedicated maimai CV or auto-play project found.** A [maimai-android-touch-panel](https://blog.csdn.net/gitblog_01027/article/details/146904075) project exists for touch simulation but has performance issues and doesn't use ML vision. [SpiritsUnite/maimai-score-details](https://github.com/SpiritsUnite/maimai-score-details) is a browser extension for score analysis, not CV.

## Summary

| Area | Status |
|---|---|
| Chart generation | 1 academic paper (no code), 1 experimental GPT wrapper |
| Training data | HuggingFace dataset exists (~1,394 charts) |
| Difficulty analysis | None |
| Computer vision | None |
| Score prediction | None |
| Auto-play | None |
| Adjacent tools | MuG-Diffusion (maimai on roadmap), Zhihu GRU article |

**The field is wide open for a first-mover.**
