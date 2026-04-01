# Existing AI Projects for Rhythm Games

## 1. AI Players / Bots

### Memory-reading / Algorithmic Bots
- [CookieHoodie/OsuBot](https://github.com/CookieHoodie/OsuBot) — Auto, Relax, Autopilot mods for osu! via game memory reading
- [KuromeSama6/Autosu](https://github.com/KuromeSama6/Autosu) — osu! autopilot with full UI, simulates human-like hand movement
- [vicb0/Py-OsuAuto](https://github.com/victorborneo/Py-OsuAuto) — Pure Python osu! bot
- [aci2n/osu-autoplay-bot](https://github.com/aci2n/osu-autoplay-bot) — Minimal osu! autoplay bot

### ML-based Players
- [GuiBrandt/OsuLearn](https://github.com/GuiBrandt/OsuLearn) — Neural network trained on human replay data for human-like osu! replays
- [joshuatmyers/osu-ai](https://github.com/joshuatmyers/osu-ai) — OpenCV template matching + CNN (fastAI) to play osu! via screen reading

## 2. AI Chart / Beatmap Generators

- [OliBomby/Mapperatorinator](https://github.com/OliBomby/Mapperatorinator) — The most advanced. Multi-model framework for all 4 osu! gamemodes from spectrogram inputs. Has web UI and [Colab notebook](https://colab.research.google.com/github/OliBomby/Mapperatorinator/blob/main/colab/mapperatorinator_inference.ipynb). v2 fork: [Tiger14n/Mapperatorinator2](https://github.com/Tiger14n/Mapperatorinator2)
- [Keytoyze/Mug-Diffusion](https://github.com/Keytoyze/Mug-Diffusion) — Stable Diffusion-based, 4K VSRG charts. Supports difficulty control. ~30s per song on 3050Ti
- [jaswon/osu-dreamer](https://github.com/jaswon/osu-dreamer) — Diffusion-based osu! map generation from raw audio
- [gyataro/osuT5](https://github.com/gyataro/osuT5) — T5 transformer for osu! beatmaps from spectrograms
- [kotritrona/osumapper](https://github.com/kotritrona/osumapper) — Early TensorFlow-based generator. [osu! forum thread](https://osu.ppy.sh/community/forums/topics/791481)
- [sedthh/BeatLearning](https://github.com/sedthh/BeatLearning) — Open-source generative models for non-technical users
- [Garlov/AutoRhythm](https://github.com/Garlov/AutoRhythm) — Rhythm game with auto-generated maps from audio frequency analysis

## 3. Difficulty Rating Systems

- [MaxOhn/rosu-pp](https://github.com/MaxOhn/rosu-pp) — The gold standard. Rust port of osu!lazer's difficulty and PP calculation for all gamemodes. Matches official values to the last decimal. Bindings: [JavaScript](https://github.com/MaxOhn/rosu-pp-js), [Python](https://github.com/MaxOhn/rosu-pp-py), [Java](https://github.com/marcandreher/rosu-pp-jar)
- [osuAkatsuki/akatsuki-pp-py](https://github.com/osuAkatsuki/akatsuki-pp-py) — Community fork for the Akatsuki private server

Note: No widely-adopted **ML-based** difficulty rating in production — community relies on the official algorithmic star-rating (replicated by rosu-pp).

## 4. Computer Vision Approaches

- [joshuatmyers/osu-ai](https://github.com/joshuatmyers/osu-ai) — OpenCV + CNN screen reading
- [RayhaanA/OsuAutoPlay](https://github.com/RayhaanA/OsuAutoPlay) — Screen-reading auto-play
- [Medium article](https://medium.com/@florian-trautweiler/using-python-and-computer-vision-to-automate-a-browser-rhythm-game-6ae49f3a961c) — Python + CV to automate a browser-based rhythm game

## 5. Reinforcement Learning Agents

- [baballev/qsu](https://github.com/baballev/qsu) — Q-learning RL agent for osu!. Training takes 2–4 weeks.
- **Gym Hero** ([IEEE paper](https://ieeexplore.ieee.org/document/9637691/)) — Guitar Hero-like PyGame environment for training Deep Q-Network agents across 4 difficulty levels
- **OPARL** — online player-adaptive procedural content generation via RL (academic, no public repo)

## 6. Practice / Training Tools

- [Beat Aim](https://beataim.com/) — Rhythm aim trainer for FPS players with AI-generated maps
- No open-source AI-powered practice tool found on GitHub

## Key Takeaway

Beatmap generation is the most active space (Mapperatorinator and MuG-Diffusion leading). For difficulty calculation, rosu-pp is definitive. True RL agents remain mostly research-stage. **No production AI tools exist for maimai specifically.**
