import json
import numpy as np
from pathlib import Path


def load_jsonl(path):
    records = []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def find_nearest_idx(timestamps, target):
    ts = np.array(timestamps)
    return np.argmin(np.abs(ts - target))


def main():
    data_dir = Path(__file__).resolve().parent.parent.parent / "sample_data"

    force_left_file  = data_dir / "recording_force_mms101_left.jsonl"
    force_right_file = data_dir / "recording_force_mms101_right.jsonl"
    gel_left_file    = data_dir / "recording_gelsight_left.jsonl"
    gel_right_file   = data_dir / "recording_gelsight_right.jsonl"

    force_left  = load_jsonl(force_left_file)
    force_right = load_jsonl(force_right_file)
    print(f"Loaded left force records: {len(force_left)}")
    print(f"Loaded right force records: {len(force_right)}")

    force_left_times  = np.array([r["stamp"] for r in force_left])
    force_right_times = np.array([r["stamp"] for r in force_right])

    gel_left  = load_jsonl(gel_left_file)
    gel_right = load_jsonl(gel_right_file)
    print(f"Loaded left gelsight records: {len(gel_left)}")
    print(f"Loaded right gelsight records: {len(gel_right)}")

    gel_left_times  = np.array([r["timestamp"] / 1e9 for r in gel_left])
    gel_right_times = np.array([r["timestamp"] / 1e9 for r in gel_right])

    base_records = force_left
    base_times = force_left_times
    print(f"Using left force timestamps as reference. Total reference points: {len(base_times)}")

    synced = []
    for i, t in enumerate(base_times):
        idx_g_left  = find_nearest_idx(gel_left_times, t)
        idx_g_right = find_nearest_idx(gel_right_times, t)
        idx_f_right = min(i, len(force_right) - 1)

        entry = {
            "timestamp": t,
            "force_left": force_left[i],
            "force_right": force_right[idx_f_right],
            "gelsight_left": gel_left[idx_g_left],
            "gelsight_right": gel_right[idx_g_right]
        }
        synced.append(entry)

    output_file = data_dir / "synced_data.jsonl"
    with open(output_file, 'w') as f:
        for entry in synced:
            f.write(json.dumps(entry) + '\n')
    print(f"Synchronization complete. {len(synced)} records written to {output_file}")


if __name__ == "__main__":
    main()