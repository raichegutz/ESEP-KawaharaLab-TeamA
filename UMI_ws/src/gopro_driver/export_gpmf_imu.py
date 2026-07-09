#!/usr/bin/env python3
"""Export GoPro GPMF IMU streams from gpmd.bin to timestamped CSV files."""

from __future__ import annotations

import argparse
import csv
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_STREAMS = ("ACCL", "GYRO", "MAGN", "GRAV", "CORI", "IORI")
META_KEYS = {
    "STMP",
    "TSMP",
    "STNM",
    "ORIN",
    "SIUN",
    "UNIT",
    "SCAL",
    "TMPC",
    "TYPE",
    "TIMO",
    "EMPT",
    "RMRK",
}


@dataclass
class Klv:
    key: str
    type_char: str
    struct_size: int
    repeat: int
    data_start: int
    data_end: int


@dataclass
class StreamChunk:
    fourcc: str
    payload_index: int
    stmp: int | None
    tsmp: int | None
    stream_name: str
    unit: str
    orin: str
    scale: list[float]
    temperature_c: float | None
    values: list[list[float]]


def pad4(size: int) -> int:
    return (size + 3) & ~3


def iter_klv(data: bytes, start: int, end: int) -> Iterable[Klv]:
    pos = start
    while pos + 8 <= end:
        key = data[pos : pos + 4].decode("latin1", errors="replace")
        type_byte = data[pos + 4]
        type_char = chr(type_byte) if type_byte else "\0"
        struct_size = data[pos + 5]
        repeat = struct.unpack(">H", data[pos + 6 : pos + 8])[0]
        raw_size = struct_size * repeat
        data_start = pos + 8
        data_end = data_start + raw_size
        if raw_size < 0 or data_end > end:
            break
        yield Klv(key, type_char, struct_size, repeat, data_start, data_end)
        pos = data_start + pad4(raw_size)


def decode_scalar_list(type_char: str, payload: bytes) -> list[int | float | str]:
    if type_char == "s":
        return list(struct.unpack(">" + "h" * (len(payload) // 2), payload))
    if type_char == "S":
        return list(struct.unpack(">" + "H" * (len(payload) // 2), payload))
    if type_char == "l":
        return list(struct.unpack(">" + "i" * (len(payload) // 4), payload))
    if type_char == "L":
        return list(struct.unpack(">" + "I" * (len(payload) // 4), payload))
    if type_char == "j":
        return list(struct.unpack(">" + "q" * (len(payload) // 8), payload))
    if type_char == "J":
        return list(struct.unpack(">" + "Q" * (len(payload) // 8), payload))
    if type_char == "f":
        return list(struct.unpack(">" + "f" * (len(payload) // 4), payload))
    if type_char == "d":
        return list(struct.unpack(">" + "d" * (len(payload) // 8), payload))
    if type_char in {"c", "U"}:
        text = payload.split(b"\0", 1)[0]
        return [text.decode("latin1", errors="replace")]
    if type_char == "F":
        return [
            payload[i : i + 4].decode("latin1", errors="replace")
            for i in range(0, len(payload), 4)
        ]
    raise ValueError(f"Unsupported GPMF type {type_char!r}")


def decode_text(data: bytes, klv: Klv) -> str:
    return str(decode_scalar_list(klv.type_char, data[klv.data_start : klv.data_end])[0])


def decode_first_number(data: bytes, klv: Klv) -> int | float:
    values = decode_scalar_list(klv.type_char, data[klv.data_start : klv.data_end])
    if not values or isinstance(values[0], str):
        raise ValueError(f"{klv.key} does not contain a numeric value")
    return values[0]


def decode_sample_matrix(data: bytes, klv: Klv, scale: list[float]) -> list[list[float]]:
    raw = data[klv.data_start : klv.data_end]
    flat = decode_scalar_list(klv.type_char, raw)
    if not flat or isinstance(flat[0], str):
        return []

    type_size = {
        "b": 1,
        "B": 1,
        "s": 2,
        "S": 2,
        "l": 4,
        "L": 4,
        "j": 8,
        "J": 8,
        "f": 4,
        "d": 8,
    }[klv.type_char]
    elements = klv.struct_size // type_size
    if elements <= 0:
        return []

    rows: list[list[float]] = []
    for sample_i in range(klv.repeat):
        row = []
        base = sample_i * elements
        for element_i in range(elements):
            value = float(flat[base + element_i])
            if scale:
                divisor = scale[element_i % len(scale)]
                if divisor:
                    value /= divisor
            row.append(value)
        rows.append(row)
    return rows


def parse_chunks(data: bytes, stream_keys: set[str]) -> list[StreamChunk]:
    chunks: list[StreamChunk] = []
    pos = 0
    payload_index = 0

    while pos + 8 <= len(data):
        top = next(iter_klv(data, pos, len(data)), None)
        if top is None:
            break
        top_end = top.data_start + pad4(top.struct_size * top.repeat)

        if top.type_char == "\0":
            for child in iter_klv(data, top.data_start, top.data_end):
                if child.key != "STRM" or child.type_char != "\0":
                    continue

                stmp: int | None = None
                tsmp: int | None = None
                stream_name = ""
                unit = ""
                orin = ""
                scale: list[float] = []
                temperature_c: float | None = None
                sample_klv: Klv | None = None

                for entry in iter_klv(data, child.data_start, child.data_end):
                    payload = data[entry.data_start : entry.data_end]
                    if entry.key == "STMP":
                        stmp = int(decode_first_number(data, entry))
                    elif entry.key == "TSMP":
                        tsmp = int(decode_first_number(data, entry))
                    elif entry.key == "STNM":
                        stream_name = decode_text(data, entry)
                    elif entry.key in {"SIUN", "UNIT"}:
                        unit = decode_text(data, entry)
                    elif entry.key == "ORIN":
                        orin = decode_text(data, entry)
                    elif entry.key == "SCAL":
                        nums = decode_scalar_list(entry.type_char, payload)
                        scale = [float(v) for v in nums if not isinstance(v, str)]
                    elif entry.key == "TMPC":
                        temperature_c = float(decode_first_number(data, entry))
                    elif entry.key not in META_KEYS and entry.key in stream_keys:
                        sample_klv = entry

                if sample_klv:
                    chunks.append(
                        StreamChunk(
                            fourcc=sample_klv.key,
                            payload_index=payload_index,
                            stmp=stmp,
                            tsmp=tsmp,
                            stream_name=stream_name,
                            unit=unit,
                            orin=orin,
                            scale=scale,
                            temperature_c=temperature_c,
                            values=decode_sample_matrix(data, sample_klv, scale),
                        )
                    )

        pos = top_end
        payload_index += 1

    return chunks


def parse_gpsu_datetime(value: str) -> datetime | None:
    value = value.strip().strip("\0")
    try:
        dt = datetime.strptime(value, "%y%m%d%H%M%S.%f")
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc)


def infer_unix_start(data: bytes, timestamp_scale: float) -> tuple[float, str] | None:
    pos = 0

    while pos + 8 <= len(data):
        top = next(iter_klv(data, pos, len(data)), None)
        if top is None:
            break
        top_end = top.data_start + pad4(top.struct_size * top.repeat)

        if top.type_char == "\0":
            for child in iter_klv(data, top.data_start, top.data_end):
                if child.key != "STRM" or child.type_char != "\0":
                    continue

                stmp: int | None = None
                gpsu: str | None = None
                for entry in iter_klv(data, child.data_start, child.data_end):
                    if entry.key == "STMP":
                        stmp = int(decode_first_number(data, entry))
                    elif entry.key == "GPSU":
                        gpsu = decode_text(data, entry)

                if stmp is not None and gpsu:
                    dt = parse_gpsu_datetime(gpsu)
                    if dt is not None:
                        unix_start = dt.timestamp() - stmp * timestamp_scale
                        return unix_start, gpsu

        pos = top_end

    return None


def parse_orin(orin: str) -> list[tuple[str, float]]:
    axes: list[tuple[str, float]] = []
    sign = 1.0
    for char in orin.upper():
        if char == "-":
            sign = -1.0
        elif char in {"X", "Y", "Z"}:
            axes.append((char.lower(), sign))
            sign = 1.0
    return axes


def axis_map(values: list[float], orin: str) -> dict[str, float | None]:
    mapped: dict[str, float | None] = {"x": None, "y": None, "z": None}
    axes = parse_orin(orin)
    if len(axes) != len(values):
        return mapped
    for value, (axis, sign) in zip(values, axes):
        mapped[axis] = sign * value
    return mapped


def enrich_rows(
    chunks: list[StreamChunk],
    timestamp_scale: float,
    unix_start: float | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    by_stream: dict[str, list[StreamChunk]] = {}
    for chunk in chunks:
        by_stream.setdefault(chunk.fourcc, []).append(chunk)

    for fourcc, stream_chunks in sorted(by_stream.items()):
        stream_chunks.sort(key=lambda c: (c.payload_index, c.stmp or 0))
        last_dt_ticks: float | None = None
        sample_index = 0

        for chunk_i, chunk in enumerate(stream_chunks):
            if not chunk.values:
                continue

            if chunk.stmp is not None and chunk_i + 1 < len(stream_chunks):
                next_stmp = stream_chunks[chunk_i + 1].stmp
                if next_stmp is not None and next_stmp > chunk.stmp:
                    last_dt_ticks = (next_stmp - chunk.stmp) / len(chunk.values)

            dt_ticks = last_dt_ticks if last_dt_ticks is not None else 0.0
            base_ticks = float(chunk.stmp or 0)

            for sample_in_payload, values in enumerate(chunk.values):
                timestamp_s = (base_ticks + sample_in_payload * dt_ticks) * timestamp_scale
                mapped = axis_map(values, chunk.orin)

                row: dict[str, object] = {
                    "_timestamp_s_value": timestamp_s,
                    "unix_timestamp": "",
                    "timestamp_s": "",
                    "timestamp_s_rel": "",
                    "stream": fourcc,
                    "stream_name": chunk.stream_name,
                    "payload_index": chunk.payload_index,
                    "sample_index": sample_index,
                    "sample_in_payload": sample_in_payload,
                    "stmp": chunk.stmp if chunk.stmp is not None else "",
                    "tsmp": chunk.tsmp if chunk.tsmp is not None else "",
                    "unit": chunk.unit,
                    "orin": chunk.orin,
                    "scale": ";".join(f"{v:g}" for v in chunk.scale),
                    "temperature_c": (
                        f"{chunk.temperature_c:.6f}"
                        if chunk.temperature_c is not None
                        else ""
                    ),
                    "v0": values[0] if len(values) > 0 else "",
                    "v1": values[1] if len(values) > 1 else "",
                    "v2": values[2] if len(values) > 2 else "",
                    "v3": values[3] if len(values) > 3 else "",
                    "x": mapped["x"] if mapped["x"] is not None else "",
                    "y": mapped["y"] if mapped["y"] is not None else "",
                    "z": mapped["z"] if mapped["z"] is not None else "",
                }
                rows.append(row)
                sample_index += 1

    if rows:
        first_timestamp = min(float(row["_timestamp_s_value"]) for row in rows)
        for row in rows:
            timestamp_s = float(row["_timestamp_s_value"])
            if unix_start is not None:
                row["unix_timestamp"] = f"{unix_start + timestamp_s:.6f}"
            row["timestamp_s"] = f"{timestamp_s:.9f}"
            row["timestamp_s_rel"] = f"{timestamp_s - first_timestamp:.9f}"
        rows.sort(
            key=lambda row: (
                float(row["_timestamp_s_value"]),
                str(row["stream"]),
                int(row["sample_index"]),
            )
        )
        for row in rows:
            del row["_timestamp_s_value"]

    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "unix_timestamp",
        "timestamp_s",
        "timestamp_s_rel",
        "stream",
        "stream_name",
        "payload_index",
        "sample_index",
        "sample_in_payload",
        "stmp",
        "tsmp",
        "unit",
        "orin",
        "scale",
        "temperature_c",
        "v0",
        "v1",
        "v2",
        "v3",
        "x",
        "y",
        "z",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export GoPro GPMF IMU streams from gpmd.bin to CSV."
    )
    parser.add_argument("input", type=Path, help="Path to gpmd.bin")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("imu_all.csv"),
        help="Combined long-format CSV output path.",
    )
    parser.add_argument(
        "--split-dir",
        type=Path,
        default=None,
        help="Optional directory for one CSV per stream.",
    )
    parser.add_argument(
        "--streams",
        default=",".join(DEFAULT_STREAMS),
        help="Comma-separated FourCC streams to export.",
    )
    parser.add_argument(
        "--timestamp-scale",
        type=float,
        default=1e-6,
        help="Scale from STMP ticks to seconds. GoPro STMP is usually microseconds.",
    )
    parser.add_argument(
        "--unix-start",
        type=float,
        default=None,
        help=(
            "Unix timestamp, in seconds, for STMP == 0. If omitted, the script "
            "tries to infer it from GPSU."
        ),
    )
    args = parser.parse_args()

    data = args.input.read_bytes()
    stream_keys = {s.strip().upper() for s in args.streams.split(",") if s.strip()}
    chunks = parse_chunks(data, stream_keys)
    unix_start = args.unix_start
    inferred_from = None
    if unix_start is None:
        inferred = infer_unix_start(data, args.timestamp_scale)
        if inferred is not None:
            unix_start, inferred_from = inferred

    rows = enrich_rows(chunks, args.timestamp_scale, unix_start)
    write_csv(args.output, rows)

    if args.split_dir:
        for stream in sorted({str(row["stream"]) for row in rows}):
            write_csv(
                args.split_dir / f"imu_{stream}.csv",
                [row for row in rows if row["stream"] == stream],
            )

    counts: dict[str, int] = {}
    for row in rows:
        counts[str(row["stream"])] = counts.get(str(row["stream"]), 0) + 1

    print(f"Wrote {len(rows)} rows to {args.output}")
    if unix_start is not None:
        if inferred_from:
            print(f"Unix timestamp inferred from GPSU {inferred_from}")
        else:
            print(f"Unix timestamp based on --unix-start {unix_start:.6f}")
    else:
        print("Unix timestamp unavailable: pass --unix-start or include GPSU in gpmd.bin")
    for stream, count in sorted(counts.items()):
        print(f"  {stream}: {count} samples")
    if args.split_dir:
        print(f"Wrote split CSV files to {args.split_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
