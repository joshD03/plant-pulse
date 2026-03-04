import numpy as np


def compute_savings(continuous_results: dict, event_driven_results: dict) -> dict:
    """Compare total compute time and frames skipped between both detectors."""
    cont_time = sum(continuous_results["compute_times"])
    ed_time = sum(event_driven_results["compute_times"])
    time_saved_pct = ((cont_time - ed_time) / cont_time * 100) if cont_time > 0 else 0.0
    return {
        "continuous_total_ms": round(cont_time, 2),
        "event_driven_total_ms": round(ed_time, 2),
        "time_saved_pct": round(time_saved_pct, 1),
        "frames_skipped_pct": round(event_driven_results["skip_rate"] * 100, 1),
    }


def detection_agreement(continuous_results: dict, event_driven_results: dict, top_n: int = 20) -> float:
    """
    Percentage overlap between the top-N highest-change frames in both methods.
    Measures whether event-driven catches the same significant events as continuous.
    """
    cont = np.array(continuous_results["change_scores"])
    ed = np.array(event_driven_results["change_scores"])
    top_n = min(top_n, len(cont))
    overlap = len(set(np.argsort(cont)[-top_n:]) & set(np.argsort(ed)[-top_n:]))
    return round((overlap / top_n) * 100, 1)


def find_false_triggers(event_driven_results: dict, threshold_multiplier: float = 0.5) -> list:
    """
    Return indices of triggered frames where the full change score was below
    threshold_multiplier * mean_triggered_score.
    These are frames where the cheap pre-check fired but full processing found little real change.
    """
    scores = np.array(event_driven_results["change_scores"])
    triggered = np.array(event_driven_results["triggered"])
    triggered_idx = np.where(triggered)[0]
    if len(triggered_idx) == 0:
        return []
    mean_score = np.mean(scores[triggered_idx])
    return triggered_idx[scores[triggered_idx] < threshold_multiplier * mean_score].tolist()
