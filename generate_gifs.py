"""
generate_gifs.py

Produces three analytical GIFs from detector results.
Run after run_pipeline.py.

Outputs to results/figures/:
  threshold.gif       - adaptive threshold tracking slow growth vs acute events
  heatmap.gif         - cumulative change heatmap building over full time-lapse
  false_triggers.gif  - false trigger vs true trigger side-by-side anatomy
"""
import sys
import pickle
from pathlib import Path

import cv2
import numpy as np
import imageio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from src.metrics import find_false_triggers

RESULTS_DIR = Path("results/figures")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_results():
    with open("results/continuous_results.pkl", "rb") as f:
        cont = pickle.load(f)
    with open("results/event_driven_results.pkl", "rb") as f:
        ed = pickle.load(f)
    return cont, ed


def load_frames(frame_dir: str = "data/preprocessed") -> list:
    paths = sorted(Path(frame_dir).glob("*.png"))
    frames = [cv2.imread(str(p)) for p in paths]
    return [f for f in frames if f is not None]


# GIF 1: Adaptive threshold tracking
def generate_gif_threshold(cont, ed, output_path=None):
    if output_path is None:
        output_path = RESULTS_DIR / "threshold.gif"

    cont_scores = cont["change_scores"]
    thresholds = ed["thresholds"]
    triggered = ed["triggered"]
    n = len(cont_scores)
    window = 50

    # Subsample to ~120 animation frames for reasonable GIF size
    idxs = list(range(0, n, max(1, n // 120)))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.set_title("Adaptive threshold separating slow growth from acute events", fontsize=11)
    ax.set_xlabel("Frame pair")
    ax.set_ylabel("Change score")
    line_cont, = ax.plot([], [], color="steelblue", lw=1.2, label="Continuous score", alpha=0.8)
    line_thresh, = ax.plot([], [], color="darkorange", lw=2.0, label="Adaptive threshold")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    trigger_lines = []

    def init():
        line_cont.set_data([], [])
        line_thresh.set_data([], [])
        return line_cont, line_thresh

    def update(fi):
        t = idxs[fi]
        start = max(0, t - window)
        x = list(range(start, t + 1))
        yc = cont_scores[start:t + 1]
        yt = thresholds[start:t + 1]
        line_cont.set_data(x, yc)
        line_thresh.set_data(x, yt)
        ax.set_xlim(start, start + window)
        all_vals = yc + yt
        if all_vals:
            ax.set_ylim(0, max(all_vals) * 1.35 + 1e-8)
        for vl in trigger_lines:
            vl.remove()
        trigger_lines.clear()
        for idx in range(start, t + 1):
            if triggered[idx]:
                trigger_lines.append(ax.axvline(x=idx, color="crimson", alpha=0.35, lw=0.8))
        return line_cont, line_thresh

    ani = animation.FuncAnimation(fig, update, frames=len(idxs),
                                   init_func=init, blit=False, interval=80)
    ani.save(str(output_path), writer=animation.PillowWriter(fps=12))
    plt.close(fig)
    print(f"Saved: {output_path}")


# GIF 2: Cumulative change heatmap
def generate_gif_heatmap(frames, cont, output_path=None):
    if output_path is None:
        output_path = RESULTS_DIR / "heatmap.gif"

    masks = cont["masks"]
    n = min(len(frames) - 1, len(masks))
    cumulative = np.zeros_like(masks[0], dtype=np.float32)
    gif_frames = []
    step = max(1, n // 80)

    for i in range(n):
        cumulative += masks[i].astype(np.float32)
        if i % step != 0:
            continue
        norm = cv2.normalize(cumulative, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        heatmap = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        blended = cv2.addWeighted(frames[i + 1], 0.5, heatmap, 0.5, 0)
        h, w = blended.shape[:2]
        cv2.putText(blended, f"Frame {i + 1}/{n}",
                    (w - 130, h - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (255, 255, 255), 1, cv2.LINE_AA)
        gif_frames.append(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))

    imageio.mimsave(str(output_path), gif_frames, fps=10, loop=0)
    print(f"Saved: {output_path}")


# GIF 3: False trigger anatomy
def generate_gif_false_triggers(frames, ed, false_trigger_indices, output_path=None):
    if output_path is None:
        output_path = RESULTS_DIR / "false_triggers.gif"

    scores = np.array(ed["change_scores"])
    triggered = np.array(ed["triggered"])
    triggered_idx = np.where(triggered)[0]

    if len(triggered_idx) == 0:
        print("No triggered frames found, skipping false_triggers.gif.")
        return

    # Best false trigger: triggered but lowest full score
    if len(false_trigger_indices) > 0:
        best_false = false_trigger_indices[np.argmin(scores[false_trigger_indices])]
    else:
        best_false = triggered_idx[np.argmin(scores[triggered_idx])]

    # Best true trigger: highest full score
    best_true = triggered_idx[np.argmax(scores[triggered_idx])]

    def make_clip(frame_idx, label, colour_bgr, n_clip=12):
        clip = []
        for offset in range(-2, n_clip - 2):
            idx = max(1, min(int(frame_idx) + offset, len(frames) - 1))
            curr = frames[idx].copy()
            diff = cv2.absdiff(
                cv2.cvtColor(frames[idx - 1], cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY)
            )
            _, max_val, _, max_loc = cv2.minMaxLoc(diff)
            x, y = max_loc
            box = 40
            cv2.rectangle(curr,
                          (max(0, x - box), max(0, y - box)),
                          (min(curr.shape[1], x + box), min(curr.shape[0], y + box)),
                          colour_bgr, 2)
            cv2.putText(curr, label, (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, colour_bgr, 2, cv2.LINE_AA)
            cv2.putText(curr, f"score: {scores[frame_idx]:.4f}",
                        (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                        (255, 255, 255), 1, cv2.LINE_AA)
            clip.append(cv2.cvtColor(curr, cv2.COLOR_BGR2RGB))
        return clip

    gif_frames = []
    gif_frames += make_clip(best_false, "FALSE TRIGGER: background noise", (0, 0, 255))
    gif_frames += [gif_frames[-1]] * 6  # pause
    gif_frames += make_clip(best_true, "TRUE TRIGGER: growth event", (0, 200, 0))

    imageio.mimsave(str(output_path), gif_frames, fps=8, loop=0)
    print(f"Saved: {output_path}")


def main():
    print("Loading frames...")
    frames = load_frames()
    if not frames:
        print("No preprocessed frames found in data/preprocessed/. Run run_pipeline.py first.")
        sys.exit(1)

    print("Loading detector results...")
    try:
        cont, ed = load_results()
    except FileNotFoundError:
        print("Results not found. Run run_pipeline.py first.")
        sys.exit(1)

    false_trigger_indices = find_false_triggers(ed)

    print("Generating threshold.gif...")
    generate_gif_threshold(cont, ed)

    print("Generating heatmap.gif...")
    generate_gif_heatmap(frames, cont)

    print("Generating false_triggers.gif...")
    generate_gif_false_triggers(frames, ed, false_trigger_indices)

    print("\nAll GIFs saved to results/figures/")


if __name__ == "__main__":
    main()
