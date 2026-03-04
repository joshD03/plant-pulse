"""
run_pipeline.py

Runs the full plant-pulse pipeline end to end:
  1. Generates synthetic data if no dataset found
  2. Preprocesses frames
  3. Runs continuous and event-driven detectors
  4. Saves results to results/
  5. Prints summary

Then run: python generate_gifs.py
"""
import pickle
from pathlib import Path
from src.preprocessing import preprocess_frames
from src.continuous import continuous_detector
from src.event_driven import event_driven_detector
from src.metrics import compute_savings, detection_agreement, find_false_triggers


def main():
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    data_dir = Path("data/komatsuna")
    if not data_dir.exists() or not list(data_dir.glob("*.png")):
        print("No dataset found in data/komatsuna/. Generating synthetic data...")
        from generate_synthetic_data import generate_synthetic_frames
        generate_synthetic_frames()

    print("\n--- Preprocessing ---")
    frames = preprocess_frames("data/komatsuna", "data/preprocessed")

    print("\n--- Continuous detector ---")
    cont = continuous_detector(frames)

    print("\n--- Event-driven detector (alpha=0.95, sensitivity=1.5) ---")
    ed = event_driven_detector(frames, alpha=0.95, sensitivity=1.5)

    with open(results_dir / "continuous_results.pkl", "wb") as f:
        pickle.dump(cont, f)
    with open(results_dir / "event_driven_results.pkl", "wb") as f:
        pickle.dump(ed, f)
    print("Results saved to results/")

    savings = compute_savings(cont, ed)
    agreement = detection_agreement(cont, ed, top_n=20)
    false_triggers = find_false_triggers(ed)

    print("\n========== RESULTS SUMMARY ==========")
    print(f"Total frame pairs:            {cont['total_frames_processed']}")
    print(f"Event-driven triggered:       {ed['total_frames_processed']} frames")
    print(f"Frames skipped:               {savings['frames_skipped_pct']}%")
    print(f"Continuous compute time:      {savings['continuous_total_ms']} ms")
    print(f"Event-driven compute time:    {savings['event_driven_total_ms']} ms")
    print(f"Compute time saved:           {savings['time_saved_pct']}%")
    print(f"Detection agreement (top-20): {agreement}%")
    print(f"False triggers identified:    {len(false_triggers)}")
    print("=====================================")
    print("\nNext step: python generate_gifs.py")


if __name__ == "__main__":
    main()
