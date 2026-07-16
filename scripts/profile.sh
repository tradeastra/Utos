#!/bin/bash
# ─────────────────────────────────────────────
# Sprint 16F-5: Profiling Script
#
# Tools:
#   py-spy  — sampling profiler (low overhead)
#   scalene — CPU + memory profiler
#   memray  — memory allocation tracker
#
# Usage:
#   bash scripts/profile.sh [tool] [duration]
#   tool: pyspy | scalene | memray (default: pyspy)
#   duration: seconds (default: 60)
# ─────────────────────────────────────────────

set -e

TOOL="${1:-pyspy}"
DURATION="${2:-60}"
OUTPUT_DIR="${PROFILE_DIR:-/tmp/utos-profiles}"
mkdir -p "$OUTPUT_DIR"

# Find the uvicorn process
PID=$(pgrep -f "uvicorn.*main:app" | head -1)

if [ -z "$PID" ]; then
    echo "No uvicorn process found. Starting one..."
    cd /app/backend
    uvicorn main:app --host 0.0.0.0 --port 8000 &
    PID=$!
    sleep 5
fi

echo "Profiling PID: $PID"
echo "Tool: $TOOL"
echo "Duration: ${DURATION}s"
echo "Output: $OUTPUT_DIR"
echo ""

case "$TOOL" in
    pyspy)
        echo "Starting py-spy sampling profiler..."
        py-spy record \
            --pid "$PID" \
            --duration "$DURATION" \
            --output "$OUTPUT_DIR/pyspy-flamegraph.svg" \
            --format flamegraph
        echo "Flamegraph saved to: $OUTPUT_DIR/pyspy-flamegraph.svg"

        # Also dump raw samples
        py-spy dump --pid "$PID" > "$OUTPUT_DIR/pyspy-dump.txt" 2>&1 || true
        echo "Stack dump saved to: $OUTPUT_DIR/pyspy-dump.txt"
        ;;

    scalene)
        echo "Starting scalene CPU+memory profiler..."
        # Scalene needs to start the process itself
        cd /app/backend
        timeout "$DURATION" python -m scalene \
            --html \
            --output "$OUTPUT_DIR/scalene-report.html" \
            main.py 2>&1 || true
        echo "Scalene report saved to: $OUTPUT_DIR/scalene-report.html"
        ;;

    memray)
        echo "Starting memray memory profiler..."
        cd /app/backend
        timeout "$DURATION" python -m memray run \
            --output "$OUTPUT_DIR/memray-output.bin" \
            -m uvicorn main:app --host 0.0.0.0 --port 8000 2>&1 || true

        # Generate flamegraph from memray data
        python -m memray flamegraph \
            "$OUTPUT_DIR/memray-output.bin" \
            --output "$OUTPUT_DIR/memray-flamegraph.html" 2>&1 || true

        # Generate stats summary
        python -m memray stats \
            "$OUTPUT_DIR/memray-output.bin" > "$OUTPUT_DIR/memray-stats.txt" 2>&1 || true

        echo "Memray data saved to: $OUTPUT_DIR/memray-output.bin"
        echo "Memray flamegraph: $OUTPUT_DIR/memray-flamegraph.html"
        echo "Memray stats: $OUTPUT_DIR/memray-stats.txt"
        ;;

    *)
        echo "Unknown tool: $TOOL"
        echo "Available: pyspy, scalene, memray"
        exit 1
        ;;
esac

echo ""
echo "Profiling complete. Results in: $OUTPUT_DIR"
