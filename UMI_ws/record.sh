#!/usr/bin/env bash

# usage: ./record.sh [num_episodes] [episode_duration_sec] [data_root]

set -euo pipefail

usage() {
    echo "Usage: $0 [num_episodes] [episode_duration_sec] [data_root]"
    echo "Example: $0 10 15.0 ./data"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

num_episodes="${1:-1}"
episode_duration_sec="${2:-10.0}"
workspace_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
data_root="${3:-${workspace_dir}/data}"

if ! [[ "${num_episodes}" =~ ^[1-9][0-9]*$ ]]; then
    echo "Error: num_episodes must be a positive integer." >&2
    usage >&2
    exit 2
fi

if ! [[ "${episode_duration_sec}" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] ||
    [[ "${episode_duration_sec}" =~ ^0*([.]0*)?$ ]]; then
    echo "Error: episode_duration_sec must be a positive number." >&2
    usage >&2
    exit 2
fi

exec ros2 launch sensor_framework launch.py \
    "num_episodes:=${num_episodes}" \
    "episode_duration_sec:=${episode_duration_sec}" \
    "data_root:=${data_root}"
