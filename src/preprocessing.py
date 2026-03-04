import cv2
import numpy as np
import logging
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preprocess_frames(frame_dir: str, output_dir: str = "data/preprocessed") -> list:
    """
    Load and preprocess all PNG frames from frame_dir.

    Steps:
    1. CLAHE illumination correction (handles LED drift between frames)
    2. ORB-based registration to frame 0 (corrects camera vibration)
    3. Gaussian blur (suppresses high-frequency sensor noise)

    Returns list of preprocessed BGR frames.
    """
    frame_dir = Path(frame_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = sorted(frame_dir.glob("*.png"))
    if not frame_paths:
        raise FileNotFoundError(f"No PNG frames found in {frame_dir}")

    logger.info(f"Loading {len(frame_paths)} frames from {frame_dir}")
    raw_frames = []
    for p in tqdm(frame_paths, desc="Loading"):
        frame = cv2.imread(str(p))
        if frame is None:
            logger.warning(f"Could not read {p}, skipping.")
            continue
        raw_frames.append(frame)

    if not raw_frames:
        raise ValueError("No frames could be loaded.")

    # Step 1: CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    def apply_clahe(frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        lab_clahe = cv2.merge((clahe.apply(l), a, b))
        return cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)

    clahe_frames = [apply_clahe(f) for f in tqdm(raw_frames, desc="CLAHE")]

    # Step 2: ORB registration to frame 0
    reference = clahe_frames[0]
    ref_gray = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=500)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    kp_ref, des_ref = orb.detectAndCompute(ref_gray, None)

    registered = [reference]
    for i, frame in enumerate(tqdm(clahe_frames[1:], desc="Registering"), 1):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        kp, des = orb.detectAndCompute(gray, None)
        if des is None or des_ref is None or len(kp) < 10:
            logger.warning(f"Frame {i}: insufficient keypoints, skipping registration.")
            registered.append(frame)
            continue
        matches = sorted(bf.match(des_ref, des), key=lambda x: x.distance)
        if len(matches) < 10:
            logger.warning(f"Frame {i}: only {len(matches)} matches, skipping registration.")
            registered.append(frame)
            continue
        src_pts = np.float32([kp_ref[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        H, _ = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)
        if H is None:
            logger.warning(f"Frame {i}: homography failed, skipping.")
            registered.append(frame)
            continue
        h, w = reference.shape[:2]
        registered.append(cv2.warpPerspective(frame, H, (w, h)))

    # Step 3: Gaussian blur
    blurred = [cv2.GaussianBlur(f, (5, 5), 0) for f in tqdm(registered, desc="Blur")]

    for i, frame in enumerate(blurred):
        cv2.imwrite(str(output_dir / f"frame_{i:04d}.png"), frame)

    logger.info(f"Saved {len(blurred)} preprocessed frames to {output_dir}")
    return blurred
