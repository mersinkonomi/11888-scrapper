#!/usr/bin/env bash

set -u

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir" || exit 1

if [[ -x "$script_dir/.venv/bin/python" ]]; then
    python_bin="$script_dir/.venv/bin/python"
else
    python_bin="python3"
fi

lock_dir="$script_dir/.run_10_workers.lock"
pids=()

cleanup() {
    exit_status=$?
    trap - EXIT INT TERM

    running_pids=()
    while IFS= read -r pid; do
        if [[ -n "$pid" ]]; then
            running_pids+=("$pid")
        fi
    done < <(jobs -pr)

    if ((${#running_pids[@]} > 0)); then
        echo "Stopping ${#running_pids[@]} worker(s)..."
        for pid in "${running_pids[@]}"; do
            kill -TERM "$pid" 2>/dev/null || true
        done
        wait 2>/dev/null || true
    fi

    if [[ -f "$lock_dir/pid" ]]; then
        lock_owner=""
        IFS= read -r lock_owner < "$lock_dir/pid" || true
        if [[ "$lock_owner" == "$$" ]]; then
            unlink "$lock_dir/pid" 2>/dev/null || true
            rmdir "$lock_dir" 2>/dev/null || true
        fi
    fi

    exit "$exit_status"
}

handle_signal() {
    echo
    echo "Stop requested."
    exit 130
}

if ! mkdir "$lock_dir" 2>/dev/null; then
    existing_pid=""
    if [[ -f "$lock_dir/pid" ]]; then
        IFS= read -r existing_pid < "$lock_dir/pid" || true
    fi

    if [[ "$existing_pid" =~ ^[0-9]+$ ]] && kill -0 "$existing_pid" 2>/dev/null; then
        echo "Another 10-worker run is already active (PID $existing_pid)." >&2
        exit 1
    fi

    unlink "$lock_dir/pid" 2>/dev/null || true
    rmdir "$lock_dir" 2>/dev/null || true
    if ! mkdir "$lock_dir" 2>/dev/null; then
        echo "Could not acquire launcher lock: $lock_dir" >&2
        exit 1
    fi
fi

printf '%s\n' "$$" > "$lock_dir/pid"
trap cleanup EXIT
trap handle_signal INT TERM

total_pages=100000000
worker_count=10
chunk_size=$((total_pages / worker_count))
startup_delay=2
run_id="$(date '+%Y%m%d_%H%M%S')"
log_dir="$script_dir/logs/$run_id"
mkdir -p "$log_dir"

for ((worker=0; worker<worker_count; worker++)); do
    start=$((worker * chunk_size))
    end=$(((worker + 1) * chunk_size))
    log_file="$log_dir/worker_${worker}.log"

    echo "Starting worker ${worker}: ${start}-$((end - 1)) (log: ${log_file})"
    "$python_bin" -u autoscrap.py \
        --start "$start" \
        --end "$end" \
        > "$log_file" 2>&1 &
    pids+=("$!")

    if ((worker + 1 < worker_count)); then
        sleep "$startup_delay"
    fi
done

status=0
for pid in "${pids[@]}"; do
    if ! wait "$pid"; then
        status=1
    fi
done

if ((status == 0)); then
    echo "All workers completed successfully."
else
    echo "One or more workers failed. Check logs in: $log_dir" >&2
fi

exit "$status"
