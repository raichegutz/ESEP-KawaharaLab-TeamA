import json
import argparse
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
    idx = np.searchsorted(timestamps, target, side='left')
    if idx == 0:
        return 0
    if idx == len(timestamps):
        return len(timestamps) - 1
    before = timestamps[idx - 1]
    after  = timestamps[idx]
    if abs(after - target) < abs(before - target):
        return idx
    else:
        return idx - 1


def to_nanoseconds(ts):
    ts = np.asarray(ts, dtype=np.float64)
    result = np.empty(ts.shape, dtype=np.int64)
    for i, val in enumerate(ts):
        if val > 1e12:
            result[i] = int(val)
        else:
            sec_int = int(val)                     
            sec_frac = val - sec_int               
            ns_int = sec_int * 1000000000   
            ns_frac = int(np.round(sec_frac * 1e9))
            result[i] = ns_int + ns_frac
    return result


def main():
    parser = argparse.ArgumentParser(description="Synchronize force and Gelsight data")
    parser.add_argument(
        "--data-dir", "-d",
        default=str(Path(__file__).resolve().parent.parent.parent / "sample_data"),
        help="Path to the directory containing the recorded JSONL files")
    
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    force_left_file  = data_dir / "recording_force_mms101_left.jsonl"
    force_right_file = data_dir / "recording_force_mms101_right.jsonl"
    gel_left_file    = data_dir / "recording_gelsight_left.jsonl"
    gel_right_file   = data_dir / "recording_gelsight_right.jsonl"

    force_left  = load_jsonl(force_left_file)
    force_right = load_jsonl(force_right_file)
    print(f"Loaded left force records: {len(force_left)}")
    print(f"Loaded right force records: {len(force_right)}")

    force_left_times  = to_nanoseconds([r["stamp"] for r in force_left])
    force_right_times = to_nanoseconds([r["stamp"] for r in force_right])

    gel_left  = load_jsonl(gel_left_file)
    gel_right = load_jsonl(gel_right_file)
    print(f"Loaded left gelsight records: {len(gel_left)}")
    print(f"Loaded right gelsight records: {len(gel_right)}")

    gel_left_times  = to_nanoseconds([r["timestamp"] for r in gel_left])
    gel_right_times = to_nanoseconds([r["timestamp"] for r in gel_right])

    if not all([force_left, force_right, gel_left, gel_right]):
        print("Error: One or more input streams are empty. Aborting.")
        return
    
    force_right_ts = np.array(force_right_times)
    gel_left_ts    = np.array(gel_left_times)
    gel_right_ts   = np.array(gel_right_times)

    base_times = force_left_times
    print(f"Using left force timestamps as reference. Total reference points: {len(base_times)}")

    MAX_DIFF_NS = int(0.1 * 1e9)

    synced = []
    skipped = 0
    for i, t in enumerate(base_times):
        idx_f_right = find_nearest_idx(force_right_ts, t)
        diff_f_right = abs(int(force_right_ts[idx_f_right]) - int(t))

        idx_g_left  = find_nearest_idx(gel_left_ts, t)
        diff_g_left  = abs(int(gel_left_ts[idx_g_left]) - int(t))

        idx_g_right = find_nearest_idx(gel_right_ts, t)
        diff_g_right = abs(int(gel_right_ts[idx_g_right]) - int(t))

        if diff_f_right > MAX_DIFF_NS or diff_g_left > MAX_DIFF_NS or diff_g_right > MAX_DIFF_NS:
            skipped += 1
            continue

        entry = {
            "timestamp": int(t),
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
    print(f"Skipped {skipped} records due to time difference > {MAX_DIFF_NS}ns")


if __name__ == "__main__":
    main()