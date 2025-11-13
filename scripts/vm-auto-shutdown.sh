#!/bin/bash
# Auto-shutdown script for VM (runs ON the VM)
# Shuts down the VM after a period of idle time with no active connections

# Configuration
IDLE_TIMEOUT_MINUTES=120  # 2 hours (same as Cloud Workstation default)
CHECK_INTERVAL_SECONDS=300  # Check every 5 minutes

get_active_connections() {
    # Count active SSH sessions and code-server connections
    SSH_COUNT=$(who | wc -l)
    CODESERVER_COUNT=$(ss -tn | grep :8080 | grep ESTAB | wc -l)
    TOTAL=$((SSH_COUNT + CODESERVER_COUNT))
    echo $TOTAL
}

# Track idle time
IDLE_MINUTES=0

echo "Auto-shutdown monitor started"
echo "Will shutdown after ${IDLE_TIMEOUT_MINUTES} minutes of inactivity"
echo "Checking every ${CHECK_INTERVAL_SECONDS} seconds"

while true; do
    ACTIVE=$(get_active_connections)

    if [ "$ACTIVE" -gt 0 ]; then
        # Active connections - reset idle counter
        if [ "$IDLE_MINUTES" -gt 0 ]; then
            echo "$(date): Activity detected, resetting idle timer (was at ${IDLE_MINUTES}m)"
        fi
        IDLE_MINUTES=0
    else
        # No active connections - increment idle counter
        IDLE_MINUTES=$((IDLE_MINUTES + CHECK_INTERVAL_SECONDS / 60))
        echo "$(date): No activity for ${IDLE_MINUTES} minutes (shutdown at ${IDLE_TIMEOUT_MINUTES}m)"

        if [ "$IDLE_MINUTES" -ge "$IDLE_TIMEOUT_MINUTES" ]; then
            echo "$(date): Idle timeout reached. Shutting down..."
            sudo shutdown -h now
            exit 0
        fi
    fi

    sleep $CHECK_INTERVAL_SECONDS
done
