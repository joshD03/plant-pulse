import cv2
import numpy as np
import time
from tqdm import tqdm


def event_driven_detector(
    frames: list,
    alpha: float = 0.95,
    sensitivity: float = 1.5,
    pixel_threshold: int = 15,
) -> dict:
    """
    Event-driven detector using an adaptive exponential moving average threshold.

    The system computes a cheap 32x32 pre-check on every frame pair.
    Full processing only runs when the cheap score exceeds sensitivity * adaptive_threshold.
    The adaptive threshold tracks slow baseline variation (e.g. steady growth, lighting drift)
    without storing long historical windows in memory.

    This directly addresses the core algorithmic tension in event-driven plant sensing:
    separating slow physiological change from acute stress responses at minimal compute cost.

    Args:
        frames: list of preprocessed BGR frames
        alpha: EMA smoothing (higher = slower threshold adaptation)
        sensitivity: how many multiples above baseline triggers full processing
        pixel_threshold: intensity difference for binary mask in full processing

    Returns dict:
        change_scores: full score if triggered, 0.0 if skipped
        thresholds: adaptive threshold value at each frame pair
        triggered: bool list
        compute_times: ms per frame pair
        total_frames_processed: count of triggered frames
        skip_rate: fraction of frame pairs skipped
    """
    SMALL = (32, 32)

    def cheap_score(f1, f2):
        s1 = cv2.resize(cv2.cvtColor(f1, cv2.COLOR_BGR2GRAY), SMALL)
        s2 = cv2.resize(cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY), SMALL)
        return np.mean(cv2.absdiff(s1, s2)) / 255.0

    # Initialise adaptive threshold from first 10 pairs
    init = [cheap_score(frames[i - 1], frames[i]) for i in range(1, min(11, len(frames)))]
    adaptive_threshold = float(np.mean(init)) if init else 0.01

    change_scores, thresholds, triggered_flags, compute_times = [], [], [], []
    total_triggered = 0

    for i in tqdm(range(1, len(frames)), desc="Event-driven detection"):
        t0 = time.perf_counter()

        c = cheap_score(frames[i - 1], frames[i])
        adaptive_threshold = alpha * adaptive_threshold + (1 - alpha) * c
        thresholds.append(adaptive_threshold)

        if c > sensitivity * adaptive_threshold:
            diff = cv2.absdiff(
                cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            )
            _, mask = cv2.threshold(diff, pixel_threshold, 255, cv2.THRESH_BINARY)
            score = np.count_nonzero(mask) / mask.size
            triggered = True
            total_triggered += 1
        else:
            score = 0.0
            triggered = False

        compute_times.append((time.perf_counter() - t0) * 1000)
        change_scores.append(score)
        triggered_flags.append(triggered)

    total_pairs = len(frames) - 1
    skip_rate = 1.0 - (total_triggered / total_pairs) if total_pairs > 0 else 0.0

    return {
        "change_scores": change_scores,
        "thresholds": thresholds,
        "triggered": triggered_flags,
        "compute_times": compute_times,
        "total_frames_processed": total_triggered,
        "skip_rate": skip_rate,
    }
