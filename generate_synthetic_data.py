"""
Generates 200 synthetic plant growth time-lapse frames.

Simulates:
- A growing green circle on a soil-coloured background (plant growth)
- Per-frame Gaussian noise (sensor noise)
- Occasional brightness steps (LED illumination flicker)
- Small random translations per frame (camera vibration / fan)
- Stress event at frames 80-90: sudden darkening of the plant region

Use this if the KOMATSUNA dataset is unavailable.
"""
import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm


def generate_synthetic_frames(
    output_dir: str = "data/komatsuna",
    n_frames: int = 200,
    width: int = 320,
    height: int = 240,
    seed: int = 42,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)
    cx, cy = width // 2, height // 2
    base_radius = 20

    for i in tqdm(range(n_frames), desc="Generating synthetic frames"):
        # Soil background
        frame = np.full((height, width, 3), (34, 68, 54), dtype=np.uint8)

        radius = int(base_radius + i * 0.3)

        # Camera vibration
        dx, dy = int(rng.integers(-2, 3)), int(rng.integers(-2, 3))
        plant_cx, plant_cy = cx + dx, cy + dy

        cv2.circle(frame, (plant_cx, plant_cy), radius, (34, 139, 34), -1)
        cv2.circle(frame, (plant_cx, plant_cy), radius, (0, 100, 0), 2)

        # Illumination flicker (5% of frames)
        if rng.random() < 0.05:
            delta = int(rng.integers(20, 50))
            frame = np.clip(frame.astype(np.int16) + delta, 0, 255).astype(np.uint8)

        # Gaussian noise
        noise = rng.integers(0, 12, frame.shape, dtype=np.uint8)
        frame = cv2.add(frame, noise)

        # Stress event: sudden darkening of plant at frames 80-90
        if 80 <= i <= 90:
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.circle(mask, (plant_cx, plant_cy), radius, 255, -1)
            frame[mask == 255] = (frame[mask == 255] * 0.55).astype(np.uint8)

        cv2.imwrite(str(output_dir / f"frame_{i:04d}.png"), frame)

    print(f"\nGenerated {n_frames} synthetic frames in {output_dir}")
    print("Stress event injected at frames 80-90 for detection validation.")


if __name__ == "__main__":
    generate_synthetic_frames()
