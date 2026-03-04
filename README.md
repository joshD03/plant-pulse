# plant-pulse

Comparing event-driven and continuous change detection on plant growth time-lapses, with a focus on compute efficiency.

***

![Threshold GIF](results/figures/threshold.gif)
*Adaptive threshold (orange) tracking baseline variation against the raw continuous score (blue). Red markers show when the event-driven detector triggered. The stress event at frames 80 to 90 produces a clear spike above the baseline.*

***

## Summary

* **Goal:** compare event-driven versus continuous change detection on plant time-lapse imagery
* **Dataset:** 200 synthetic frames (lettuce-style growth, injected stress event at frames 80 to 90)
* **Detectors:** continuous (every frame) versus adaptive EMA threshold with 32x32 pre-check
* **Result:** 91.5% of frames skipped, 22.2% compute time saved, 70% detection agreement on top-20 events
* **Main finding:** the pre-check overhead in Python closes the gap between skip rate and actual time saved; on dedicated hardware that gap largely disappears
* **Time spent:** one day

Built to get comfortable with time-lapse image pipelines before applying to a project on event-driven plant sensing.

***

## Motivation

Most automated plant monitoring systems rely on continuous imaging, which is energy-intensive and difficult to scale. The question here is whether a system can let plant behaviour itself trigger sensing and computation, rather than running constantly regardless of whether anything has changed.

I was specifically interested in one problem: how do you separate a slow, gradual change like steady growth from an acute event like a stress response, without storing a long history of the plant in memory? The adaptive threshold is my attempt at that.

I had not worked with image or time-lapse data before this. I wanted to build the preprocessing pipeline from scratch (illumination correction, frame registration, noise suppression) rather than starting from a clean dataset, because that is where most of the work actually is.

***

## Results at a glance

* Frames skipped: **91.5%** (182 of 199 frame pairs)
* Compute time saved: **22.2%** (11.27 ms continuous vs 8.76 ms event-driven)
* Detection agreement (top-20 events): **70%** (14 of 20 events matched)
* False triggers: **3 of 17** triggered frames (17.6%)
* Worst false trigger score: **0.0914**
* Ground truth stress event (frames 80 to 90): detected

***

## GIFs

### Adaptive threshold tracking
![Threshold GIF](results/figures/threshold.gif)

The threshold adapts slowly upward as the plant grows, tracking the gradual increase in baseline frame-to-frame difference without treating it as an event. The stress event at frames 80 to 90 pushes the raw score well above the threshold and triggers correctly. Change scores stay between 0.0 and 0.35 across the full sequence.

### Cumulative change heatmap
![Heatmap GIF](results/figures/heatmap.gif)

Per-pixel accumulation of detected change across all 199 frame pairs. The plant growth region accumulates most of the change (orange-red), while the background stays cold (blue). Watching it build frame by frame makes the spatial pattern of biological activity visible in a way a single frame cannot.

### False trigger vs true trigger
![False trigger GIF](results/figures/false_triggers.gif)

The worst false trigger scored 0.0914. The 32x32 pre-check fired, but full-resolution processing found very little real change. Most likely camera vibration or a brief illumination flicker. Shown back to back with the strongest true trigger (the injected stress event) to make the contrast clear.

***

## How it works

### Preprocessing

Three steps before either detector runs:

1. **CLAHE** on the L channel of each frame (LAB colour space) to correct for LED illumination drift across sessions
2. **ORB-based registration** to frame 0, correcting small camera translations using feature matching and a homography
3. **Gaussian blur** (5x5) to suppress high-frequency sensor noise before differencing

These are the three main sources of spurious frame-to-frame variation in a typical growth chamber setup. If any of them are left uncorrected, the detectors produce false triggers constantly.

### Continuous detector

Absolute pixel difference on every frame pair, threshold at intensity 15, change score as fraction of pixels above threshold. Processes all 199 pairs.

### Event-driven detector

A cheap 32x32 downsampled difference runs on every frame pair. The full pipeline only runs when that score exceeds `sensitivity * adaptive_threshold`.

The adaptive threshold updates as:

```
threshold(t) = alpha * threshold(t-1) + (1 - alpha) * cheap_score(t)
```

Initialised from the mean of the first 10 frame pairs. With alpha = 0.95, the threshold adapts slowly enough to track steady growth without masking genuine events, but fast enough to re-stabilise after the stress event passes.

***

## Discussion

### On the compute savings gap

91.5% of frames were skipped but only 22.2% of compute time was saved. This is because the 32x32 pre-check still runs on every frame in Python, so skipped frames are not free. On a real embedded or FPGA implementation the pre-check cost is negligible and savings would track the skip rate much more closely. The gap is a software prototype artefact rather than a fundamental property of the approach.

### On detection agreement

70% agreement on the top-20 events means 6 events were caught by continuous sensing but missed by event-driven. The next step would be to inspect those 6 frames individually and check whether they were genuine biological events that the threshold smoothed over, or high-noise frames that continuous sensing incorrectly ranked as significant. That distinction matters a lot for calibrating alpha and sensitivity on a real dataset.

### On false triggers

3 false triggers out of 17 total is a 17.6% false positive rate. Per-region masking (processing only the plant pixels rather than the full frame) would be the most straightforward way to reduce this, since most false triggers came from background motion at the frame edges.

***

## Limitations

* The adaptive threshold breaks after a sudden lighting change (for example an LED spectrum switch). It produces burst false triggers until the baseline re-adapts.
* The 32x32 pre-check loses spatial detail. Small but biologically significant changes may never trigger full processing.
* The whole frame is treated as a single region. Any background motion contributes to the pre-check score.
* The synthetic dataset uses a circle growing at a fixed rate. Real plant growth has pauses, asymmetric expansion, and leaf overlap, which would stress the threshold in different ways.
* Extending this to Arabidopsis would need calibration of alpha and sensitivity against ground-truth stress annotations, since its growth dynamics are quite different from lettuce.

***

## Dataset

Targeted at the **KOMATSUNA dataset** (Kyushu University, lettuce time-lapse imagery, used in published plant phenotyping work).

> Uchiyama, H. et al. *Easy Accessibility to KOMATSUNA Dataset.* ICCV Workshop on Computer Vision Problems in Plant Phenotyping, 2017.
> http://limu.ait.kyushu-u.ac.jp/dataset/en/

All results here used synthetic data generated by `generate_synthetic_data.py`. The synthetic frames simulate growth, noise, illumination flicker, camera vibration, and an injected stress event at frames 80 to 90 as a ground truth validation target.

***

## Repository structure

```text
plant-pulse/
README.md
requirements.txt
generate_synthetic_data.py
run_pipeline.py
generate_gifs.py
src/
  preprocessing.py
  continuous.py
  event_driven.py
  metrics.py
data/
  komatsuna/        (not committed, add your own frames here)
  preprocessed/     (generated by run_pipeline.py)
results/
  figures/          (GIF outputs)
```

***

## Usage

```bash
git clone https://github.com/joshD03/plant-pulse
cd plant-pulse
pip install -r requirements.txt

python run_pipeline.py      # generates synthetic data automatically if data/komatsuna/ is empty
python generate_gifs.py     # produces all three GIFs into results/figures/
```

***

## Dependencies

* opencv-python
* numpy
* matplotlib
* imageio
* Pillow
* scipy
* scikit-learn
* tqdm

***

## License

MIT.
