#!/bin/bash
#
# 24-Hour Monitoring Dashboard — Phase 5.6 Webhooks (5% Canary)
# Run every hour via cron or manually for spot checks
#
# Usage:
#   bash scripts/monitoring_dashboard.sh          # Current hour
#   bash scripts/monitoring_dashboard.sh all      # All 24 hours
#

set -e

# Configuration
LOG_FILE="/var/log/deltacrown-prod.log"
REPORT_DIR="./logs/canary_reports"
TIMESTAMP=$(date -u +"%Y-%m-%d_%H%M%S")

# Thresholds
SUCCESS_THRESHOLD=95
P95_THRESHOLD=2000
CB_OPENS_THRESHOLD=5
PII_TOLERANCE=0

# ANSI Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Create report directory
mkdir -p "$REPORT_DIR"

# Header
print_header() {
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}║  Webhook Canary Monitoring — Phase 5.6 (5%)                      ║${RESET}"
    echo -e "${BLUE}║  Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC" | awk '{printf "%-50s", $0}') ║${RESET}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

# Success Rate
check_success_rate() {
    local hour="$1"
    
    SUCCESS=$(grep "$hour" "$LOG_FILE" 2>/dev/null | grep "Webhook delivered successfully" | wc -l || echo 0)
    FAILED=$(grep "$hour" "$LOG_FILE" 2>/dev/null | grep "Webhook delivery failed after" | wc -l || echo 0)
    
    TOTAL=$((SUCCESS + FAILED))
    
    if [ $TOTAL -gt 0 ]; then
        SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
        
        # Color based on threshold
        if (( $(echo "$SUCCESS_RATE >= $SUCCESS_THRESHOLD" | bc -l) )); then
            COLOR=$GREEN
            STATUS="✅"
        elif (( $(echo "$SUCCESS_RATE >= 90" | bc -l) )); then
            COLOR=$YELLOW
            STATUS="⚠️ "
        else
            COLOR=$RED
            STATUS="🚨"
        fi
        
        echo -e "${COLOR}${STATUS} Success Rate: ${SUCCESS_RATE}% (${SUCCESS}/${TOTAL})${RESET}"
    else
        echo -e "${YELLOW}⚠️  No webhook data for this hour${RESET}"
    fi
}

# P95 Latency
check_p95_latency() {
    local hour="$1"
    
    # Extract latencies
    grep "$hour" "$LOG_FILE" 2>/dev/null | \
      grep "Webhook delivered successfully" | \
      grep -oP 'latency=\K[0-9]+' | \
      sort -n > /tmp/latencies_$$.txt
    
    COUNT=$(wc -l < /tmp/latencies_$$.txt)
    
    if [ $COUNT -gt 0 ]; then
        P95_LINE=$(echo "scale=0; $COUNT * 0.95 / 1" | bc)
        P95=$(sed -n "${P95_LINE}p" /tmp/latencies_$$.txt)
        
        # Color based on threshold
        if [ $P95 -lt $P95_THRESHOLD ]; then
            COLOR=$GREEN
            STATUS="✅"
        elif [ $P95 -lt 5000 ]; then
            COLOR=$YELLOW
            STATUS="⚠️ "
        else
            COLOR=$RED
            STATUS="🚨"
        fi
        
        echo -e "${COLOR}${STATUS} P95 Latency: ${P95}ms (from ${COUNT} samples)${RESET}"
    else
        echo -e "${YELLOW}⚠️  No latency data available${RESET}"
    fi
    
    rm -f /tmp/latencies_$$.txt
}

# Circuit Breaker State
check_circuit_breaker() {
    local hour="$1"
    
    CB_OPENS=$(grep "$hour" "$LOG_FILE" 2>/dev/null | grep "Circuit breaker OPENED" | wc -l || echo 0)
    CB_HALF_OPEN=$(grep "$hour" "$LOG_FILE" 2>/dev/null | grep "Circuit breaker HALF_OPEN" | wc -l || echo 0)
    CB_CLOSED=$(grep "$hour" "$LOG_FILE" 2>/dev/null | grep "Circuit breaker CLOSED" | wc -l || echo 0)
    
    # Get current state
    CURRENT_STATE=$(grep "Circuit breaker" "$LOG_FILE" 2>/dev/null | tail -1 | grep -oP '(OPENED|HALF_OPEN|CLOSED)' || echo "UNKNOWN")
    
    # Color based on opens
    if [ $CB_OPENS -eq 0 ]; then
        COLOR=$GREEN
        STATUS="✅"
    elif [ $CB_OPENS -le 1 ]; then
        COLOR=$YELLOW
        STATUS="⚠️ "
    else
        COLOR=$RED
        STATUS="🚨"
    fi
    
    echo -e "${COLOR}${STATUS} Circuit Breaker: State=${CURRENT_STATE}, Opens=${CB_OPENS}, HalfOpen=${CB_HALF_OPEN}, Closed=${CB_CLOSED}${RESET}"
}

# PII Leak Detection
check_pii_leaks() {
    echo -n "🔍 PII Scan: "
    
    # Check for emails
    EMAIL_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -iE '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b' | wc -l || echo 0)
    
    # Check for usernames (@mention style, exclude @app/@service)
    USERNAME_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -E '@[a-zA-Z0-9_]+' | grep -v '@app\|@service' | wc -l || echo 0)
    
    # Check for IP addresses
    IP_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | wc -l || echo 0)
    
    TOTAL_PII=$((EMAIL_MATCHES + USERNAME_MATCHES + IP_MATCHES))
    
    if [ $TOTAL_PII -eq 0 ]; then
        echo -e "${GREEN}✅ CLEAN (0 emails, 0 usernames, 0 IPs)${RESET}"
    else
        echo -e "${RED}🚨 LEAK DETECTED! Emails=${EMAIL_MATCHES}, Usernames=${USERNAME_MATCHES}, IPs=${IP_MATCHES}${RESET}"
        echo -e "${RED}   ⚠️  IMMEDIATE ROLLBACK REQUIRED (NOTIFICATIONS_WEBHOOK_ENABLED=False)${RESET}"
    fi
}

# Header Sample
show_header_sample() {
    echo ""
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────${RESET}"
    echo -e "${BLUE}Sample Webhook Headers (Redacted):${RESET}"
    echo ""
    
    # Extract headers from logs and redact sensitive values
    grep "X-Webhook-" "$LOG_FILE" 2>/dev/null | head -5 | \
      sed 's/[0-9a-f]\{64\}/REDACTED_SIGNATURE/g' | \
      sed 's/[0-9]\{13\}/REDACTED_TIMESTAMP/g' | \
      sed 's/[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}/REDACTED_UUID/g' || echo "No webhook headers found in logs"
    
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────${RESET}"
}

# Retry Example
show_retry_example() {
    echo ""
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────${RESET}"
    echo -e "${BLUE}Retry Example (0s → 2s → 4s):${RESET}"
    echo ""
    
    # Find a retry sequence
    grep "Webhook delivery failed" "$LOG_FILE" 2>/dev/null | \
      grep -A3 "attempt 1/3" | head -10 || echo "No retry sequences found"
    
    echo -e "${BLUE}─────────────────────────────────────────────────────────────────${RESET}"
}

# Hourly Report
generate_hourly_report() {
    local hour="$1"
    
    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${YELLOW}║  Hour: $hour (UTC)                                             ║${RESET}"
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    
    check_success_rate "$hour"
    check_p95_latency "$hour"
    check_circuit_breaker "$hour"
    check_pii_leaks
}

# 24-Hour Summary Table
generate_24h_summary() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}║  24-Hour Summary Table                                            ║${RESET}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    
    # Table header
    printf "%-20s | %10s | %10s | %12s | %12s | %10s\n" \
           "Hour (UTC)" "Delivered" "Failed" "Success %" "P95 (ms)" "CB Opens"
    echo "─────────────────────────────────────────────────────────────────────────────────"
    
    # Get start time (24 hours ago)
    START_TIME=$(date -u -d "24 hours ago" +"%Y-%m-%d %H")
    
    # Loop through 24 hours
    for i in {0..23}; do
        HOUR=$(date -u -d "$START_TIME + $i hours" +"%Y-%m-%d %H")
        
        # Success/Failed counts
        SUCCESS=$(grep "$HOUR" "$LOG_FILE" 2>/dev/null | grep "Webhook delivered successfully" | wc -l || echo 0)
        FAILED=$(grep "$HOUR" "$LOG_FILE" 2>/dev/null | grep "Webhook delivery failed after" | wc -l || echo 0)
        TOTAL=$((SUCCESS + FAILED))
        
        if [ $TOTAL -gt 0 ]; then
            SUCCESS_RATE=$(echo "scale=2; $SUCCESS * 100 / $TOTAL" | bc)
        else
            SUCCESS_RATE="N/A"
        fi
        
        # P95 latency
        grep "$HOUR" "$LOG_FILE" 2>/dev/null | \
          grep "Webhook delivered successfully" | \
          grep -oP 'latency=\K[0-9]+' | \
          sort -n > /tmp/lat_$$.txt
        
        COUNT=$(wc -l < /tmp/lat_$$.txt)
        if [ $COUNT -gt 0 ]; then
            P95_LINE=$(echo "scale=0; $COUNT * 0.95 / 1" | bc)
            P95=$(sed -n "${P95_LINE}p" /tmp/lat_$$.txt)
        else
            P95="N/A"
        fi
        rm -f /tmp/lat_$$.txt
        
        # Circuit breaker opens
        CB_OPENS=$(grep "$HOUR" "$LOG_FILE" 2>/dev/null | grep "Circuit breaker OPENED" | wc -l || echo 0)
        
        # Print row
        printf "%-20s | %10s | %10s | %12s | %12s | %10s\n" \
               "$HOUR:00" "$SUCCESS" "$FAILED" "$SUCCESS_RATE" "$P95" "$CB_OPENS"
    done
    
    echo "─────────────────────────────────────────────────────────────────────────────────"
    echo ""
}

# Overall SLO Status
check_slo_status() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BLUE}║  SLO Status (Last 24 Hours)                                       ║${RESET}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════╝${RESET}"
    echo ""
    
    # Calculate overall metrics
    START_TIME=$(date -u -d "24 hours ago" +"%Y-%m-%d %H")
    
    # Success rate
    TOTAL_SUCCESS=$(grep "Webhook delivered successfully" "$LOG_FILE" 2>/dev/null | wc -l || echo 0)
    TOTAL_FAILED=$(grep "Webhook delivery failed after" "$LOG_FILE" 2>/dev/null | wc -l || echo 0)
    TOTAL_WEBHOOKS=$((TOTAL_SUCCESS + TOTAL_FAILED))
    
    if [ $TOTAL_WEBHOOKS -gt 0 ]; then
        OVERALL_SUCCESS=$(echo "scale=2; $TOTAL_SUCCESS * 100 / $TOTAL_WEBHOOKS" | bc)
    else
        OVERALL_SUCCESS=0
    fi
    
    # P95 latency
    grep "Webhook delivered successfully" "$LOG_FILE" 2>/dev/null | \
      grep -oP 'latency=\K[0-9]+' | \
      sort -n > /tmp/all_lat_$$.txt
    
    COUNT=$(wc -l < /tmp/all_lat_$$.txt)
    if [ $COUNT -gt 0 ]; then
        P95_LINE=$(echo "scale=0; $COUNT * 0.95 / 1" | bc)
        OVERALL_P95=$(sed -n "${P95_LINE}p" /tmp/all_lat_$$.txt)
    else
        OVERALL_P95=0
    fi
    rm -f /tmp/all_lat_$$.txt
    
    # Circuit breaker opens
    TOTAL_CB_OPENS=$(grep "Circuit breaker OPENED" "$LOG_FILE" 2>/dev/null | wc -l || echo 0)
    
    # PII leaks
    EMAIL_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -iE '\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b' | wc -l || echo 0)
    USERNAME_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -E '@[a-zA-Z0-9_]+' | grep -v '@app\|@service' | wc -l || echo 0)
    IP_MATCHES=$(grep -i webhook "$LOG_FILE" 2>/dev/null | grep -oE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' | wc -l || echo 0)
    TOTAL_PII=$((EMAIL_MATCHES + USERNAME_MATCHES + IP_MATCHES))
    
    # Print SLO status
    echo "Metric                  | Target      | Actual       | Status"
    echo "────────────────────────────────────────────────────────────────"
    
    # Success rate
    if (( $(echo "$OVERALL_SUCCESS >= $SUCCESS_THRESHOLD" | bc -l) )); then
        printf "%-23s | %-11s | %-12s | %s\n" "Success Rate" "≥95%" "${OVERALL_SUCCESS}%" "$(echo -e ${GREEN}✅ PASS${RESET})"
    else
        printf "%-23s | %-11s | %-12s | %s\n" "Success Rate" "≥95%" "${OVERALL_SUCCESS}%" "$(echo -e ${RED}🚨 FAIL${RESET})"
    fi
    
    # P95 latency
    if [ $OVERALL_P95 -lt $P95_THRESHOLD ]; then
        printf "%-23s | %-11s | %-12s | %s\n" "P95 Latency" "<2000ms" "${OVERALL_P95}ms" "$(echo -e ${GREEN}✅ PASS${RESET})"
    else
        printf "%-23s | %-11s | %-12s | %s\n" "P95 Latency" "<2000ms" "${OVERALL_P95}ms" "$(echo -e ${RED}🚨 FAIL${RESET})"
    fi
    
    # Circuit breaker
    if [ $TOTAL_CB_OPENS -lt $CB_OPENS_THRESHOLD ]; then
        printf "%-23s | %-11s | %-12s | %s\n" "Circuit Breaker Opens" "<5/day" "$TOTAL_CB_OPENS" "$(echo -e ${GREEN}✅ PASS${RESET})"
    else
        printf "%-23s | %-11s | %-12s | %s\n" "Circuit Breaker Opens" "<5/day" "$TOTAL_CB_OPENS" "$(echo -e ${RED}🚨 FAIL${RESET})"
    fi
    
    # PII leaks
    if [ $TOTAL_PII -eq 0 ]; then
        printf "%-23s | %-11s | %-12s | %s\n" "PII Leaks" "0" "$TOTAL_PII" "$(echo -e ${GREEN}✅ PASS${RESET})"
    else
        printf "%-23s | %-11s | %-12s | %s\n" "PII Leaks" "0" "$TOTAL_PII" "$(echo -e ${RED}🚨 FAIL${RESET})"
    fi
    
    echo "────────────────────────────────────────────────────────────────"
    echo ""
    
    # Overall verdict
    if (( $(echo "$OVERALL_SUCCESS >= $SUCCESS_THRESHOLD" | bc -l) )) && \
       [ $OVERALL_P95 -lt $P95_THRESHOLD ] && \
       [ $TOTAL_CB_OPENS -lt $CB_OPENS_THRESHOLD ] && \
       [ $TOTAL_PII -eq 0 ]; then
        echo -e "${GREEN}✅ ALL SLOs MET — Ready for 25% canary promotion${RESET}"
    else
        echo -e "${RED}🚨 SLO BREACH — Hold at 5% or rollback${RESET}"
    fi
    echo ""
}

# Main
main() {
    print_header
    
    if [ "$1" == "all" ]; then
        # Full 24-hour report
        generate_24h_summary
        check_slo_status
        show_header_sample
        show_retry_example
        
        # Save report
        REPORT_FILE="$REPORT_DIR/canary_report_${TIMESTAMP}.txt"
        {
            print_header
            generate_24h_summary
            check_slo_status
            show_header_sample
            show_retry_example
        } > "$REPORT_FILE"
        
        echo -e "${GREEN}✅ Full report saved to: $REPORT_FILE${RESET}"
    else
        # Current hour report
        CURRENT_HOUR=$(date -u +"%Y-%m-%d %H")
        generate_hourly_report "$CURRENT_HOUR"
        show_header_sample
        show_retry_example
    fi
    
    echo ""
}

# Run
main "$@"
