# plant-pulse

Event-driven vs continuous change detection in plant growth time-lapses.

---

## Why

Controlled-environment agriculture relies almost entirely on continuous imaging to monitor crops. Most of that computation runs on frames where nothing meaningful has changed, wasting energy at scale. This project asks a precise question: can an adaptive event-driven trigger match the detection performance of continuous sensing while dramatically reducing the compute budget?

---

## The core idea

Rather than processing every frame, the detector maintains a slowly-adapting baseline of normal background variation using an exponential moving average. Full computation only fires when a cheap 32x32 pre-check exceeds a sensitivity threshold above that baseline. This means the system tracks slow, normal physiological changes like steady growth without treating them as events, while remaining sensitive to acute deviations like sudden stress responses — without storing a long history of the plant in memory.

---

## Results

### Adaptive threshold separating slow growth from acute events
![Threshold tracking](results/figures/threshold.gif)

Blue: raw per-frame change score (continuous). Orange: adaptive threshold (event-driven baseline). Red markers: frames where the event-driven detector triggered. The threshold tracks gradual illumination drift and steady growth without masking genuine biological events.

---

### Cumulative change heatmap across the full time-lapse
![Change heatmap](results/figures/heatmap.gif)

Pixel-level accumulation of detected change over the full sequence. Hot regions (orange-red) show where biological activity concentrated spatially across the growth period. Cool regions (blue) are stable background. The heatmap builds from zero, making the plant's growth trajectory visible as a physical record rather than a scalar metric.

---

### False trigger vs true trigger anatomy
![False trigger anatomy](results/figures/false_triggers.gif)

The detector does not always fire for the right reason. This clip contrasts the worst false trigger (cheap pre-check fired but full processing found minimal real change — likely fan-induced vibration or illumination flicker) against the strongest true trigger (genuine growth event). The contrast shows exactly where adaptive threshold calibration needs to improve.

---

## Key numbers

Run `python run_pipeline.py` to populate this table with your dataset.

| Metric | Value |
|---|---|
| Total frame pairs | — |
| Event-driven triggered | — |
| Frames skipped | — |
| Compute time saved | — |
| Detection agreement (top-20 events) | — |

---

## Limitations

- The adaptive threshold assumes stationarity in background variation. Sudden lighting changes (e.g. LED spectrum switching) cause burst false triggers until the threshold re-adapts.
- The 32x32 pre-check discards spatial resolution. Biologically significant but spatially small changes (e.g. single stomatal responses) may be missed entirely.
- This prototype processes the full frame. Per-plant region-of-interest masking would be needed for multi-plant trays.
- Extending to Arabidopsis specifically would require calibration of `alpha` and `sensitivity` against ground-truth stress annotations for that organism's growth dynamics.

---

## Dataset

This project uses the **KOMATSUNA dataset** — lettuce time-lapse imagery from Kyushu University, used in peer-reviewed plant phenotyping research.

> Uchiyama, H. et al. *Easy Accessibility to KOMATSUNA Dataset.* ICCV Workshop on Computer Vision Problems in Plant Phenotyping, 2017.
> Download: http://limu.ait.kyushu-u.ac.jp/dataset/en/

If the dataset is unavailable, `generate_synthetic_data.py` creates 200 synthetic frames with a growing plant, illumination flicker, camera vibration, and an injected stress event at frames 80–90 for validation.

---

## Run it

```bash
git clone https://github.com/joshD03/plant-pulse
cd plant-pulse
pip install -r requirements.txt

# Option A: no dataset needed — runs on synthetic data automatically
python run_pipeline.py

# Option B: use KOMATSUNA
# Download and place frames as data/komatsuna/frame_0000.png ...
python run_pipeline.py

# Generate all three GIFs
python generate_gifs.py
```

---

## Structure

```
plant-pulse/
├── src/
│   ├── preprocessing.py     # CLAHE illumination correction, ORB registration, Gaussian blur
│   ├── continuous.py        # Baseline: process every frame pair
│   ├── event_driven.py      # Adaptive EMA threshold trigger
│   └── metrics.py           # Savings, detection agreement, false trigger analysis
├── generate_synthetic_data.py   # Fallback synthetic dataset generator
├── run_pipeline.py              # End-to-end pipeline with printed summary
├── generate_gifs.py             # Produces all three analytical GIFs
├── requirements.txt
└── results/figures/             # GIF outputs go here
```
