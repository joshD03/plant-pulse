# plant-pulse

Comparing event-driven and continuous change detection on plant growth time-lapses, with a focus on compute efficiency.

***

![Threshold GIF](results/figures/threshold.gif)
*Adaptive threshold (orange) tracking baseline variation against the raw continuous score (blue). Red markers show when the event-driven detector triggered.*

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

## Results

### Adaptive threshold tracking
![Threshold GIF](results/figures/threshold.gif)

The threshold adapts slowly upward as the plant grows, tracking the gradual increase in baseline frame-to-frame difference without treating it as an event. The stress event at frames 80 to 90 pushes the raw score well above the threshold and triggers correctly. Change scores stay between 0.0 and 0.35 across the full sequence.

Of 199 frame pairs, the event-driven detector triggered on 17 (8.5%), skipping the remaining 91.5%. Continuous processing took 11.27 ms total versus 8.76 ms for event-driven, a 22.2% time saving. The gap between skip rate and time saved reflects the fact that the 32x32 pre-check still runs on every frame in Python and is not free. On dedicated hardware that overhead approaches zero and savings would track the skip rate directly.

### Cumulative change heatmap
![Heatmap GIF](results/figures/heatmap.gif)

Per-pixel accumulation of detected change across all 199 frame pairs. The plant region accumulates most of the change (orange-red), while the background stays cold (blue). Watching it build makes the spatial pattern of biological activity visible in a way a single summary metric cannot. The heatmap also makes clear how little of the frame is actually changing at any point, which is what makes the high skip rate plausible.

### False trigger vs true trigger
![False trigger GIF](results/figures/false_triggers.gif)

3 of the 17 triggered frames were false triggers (17.6%). The worst scored 0.0914 on the full pipeline despite the pre-check firing, consistent with a brief illumination flicker or camera vibration rather than real biological change. The clip shows that false trigger back to back with the strongest true trigger (the injected stress event) to make the contrast visible. Detection agreement on the top-20 highest-change events was 70% (14 of 20 matched). The 6 missed events are the next thing to inspect: whether they were real biological events the threshold smoothed over, or high-noise frames that continuous sensing incorrectly ranked as significant.

***

## How it works

### Preprocessing

Three steps before either detector runs:

1. **CLAHE** on the L channel of each frame to correct for LED illumination drift across sessions
2. **ORB-based registration** to frame 0, correcting small camera translations using feature matching and a homography
3. **Gaussian blur** (5x5) to suppress high-frequency sensor noise before differencing

These are the three main sources of spurious frame-to-frame variation in a typical growth chamber setup. If any are left uncorrected the detectors produce false triggers constantly.

### Continuous detector

Absolute pixel difference on every frame pair, threshold at intensity 15, change score as fraction of pixels above threshold. Processes all 199 pairs with no skipping.

### Event-driven detector

A cheap 32x32 downsampled difference runs on every frame pair. Full processing only runs when that score exceeds `sensitivity * adaptive_threshold`.

The threshold updates as:

```
threshold(t) = alpha * threshold(t-1) + (1 - alpha) * cheap_score(t)
```

Initialised from the mean of the first 10 frame pairs. With alpha = 0.95 the threshold adapts slowly enough to track steady growth without masking genuine events, but fast enough to re-stabilise after the stress event passes.

***

## Limitations

* The adaptive threshold breaks after a sudden lighting change. It produces burst false triggers until the baseline re-adapts, which is visible in the false trigger GIF.
* The 32x32 pre-check loses spatial detail. Small but biologically significant changes may never trigger full processing.
* The whole frame is treated as a single region. Any background motion contributes to the pre-check score, which is the most likely cause of the 17.6% false trigger rate here.
* The synthetic dataset uses a circle growing at a fixed rate. Real plant growth has pauses, asymmetric expansion, and leaf overlap, which would stress the threshold differently.
* Extending to Arabidopsis would need calibration of alpha and sensitivity against ground-truth stress annotations, since its growth dynamics differ from lettuce.

***

## Dataset

Targeted at the **KOMATSUNA dataset** (Kyushu University, lettuce time-lapse imagery).

> Uchiyama, H. et al. *Easy Accessibility to KOMATSUNA Dataset.* ICCV Workshop on Computer Vision Problems in Plant Phenotyping, 2017.
> http://limu.ait.kyushu-u.ac.jp/dataset/en/

All results here used synthetic data from `generate_synthetic_data.py`, which simulates growth, noise, illumination flicker, camera vibration, and an injected stress event at frames 80 to 90 as a ground truth target.

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
