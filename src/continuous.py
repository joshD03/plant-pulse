import cv2
import numpy as np
import time
from tqdm import tqdm


def continuous_detector(frames: list, pixel_threshold: int = 15) -> dict:
    """
    Baseline detector: process every consecutive frame pair regardless of content.

    Args:
        frames: list of preprocessed BGR frames
        pixel_threshold: intensity difference to count as changed pixel

    Returns dict:
        change_scores: fraction of pixels changed per frame pair
        compute_times: ms per frame pair
        masks: binary change masks
        total_frames_processed: always len(frames) - 1
    """
    change_scores, compute_times, masks = [], [], []

    for i in tqdm(range(1, len(frames)), desc="Continuous detection"):
        t0 = time.perf_counter()

        diff = cv2.absdiff(
            cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY),
            cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        )
        _, mask = cv2.threshold(diff, pixel_threshold, 255, cv2.THRESH_BINARY)
        score = np.count_nonzero(mask) / mask.size

        compute_times.append((time.perf_counter() - t0) * 1000)
        change_scores.append(score)
        masks.append(mask)

    return {
        "change_scores": change_scores,
        "compute_times": compute_times,
        "masks": masks,
        "total_frames_processed": len(frames) - 1,
    }
