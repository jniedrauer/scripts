#!/usr/bin/env bash

set -eu

main() {
    local filter="${1:-}"
    [ -n "$filter" ] || print_help "$?"
    [ "$filter" = '--help' ] && print_help "$?"

    local instances=($(filter_instances "$filter"))
    get_output_for_humans "${instances[@]}" | sort -k2,2 -n
}

get_output_for_humans() {
    local instances=("$@")
    local instance
    local load

    for instance in "${instances[@]}"; do
        load="$(get_instance_average "$instance")"
        printf '%s\t%s\n' "$instance" "$load"
    done
}

filter_instances() {
    aws ec2 describe-instances \
        --filter="$filter" \
        --query='Reservations[*].Instances[*].[InstanceId]' --output=text
}

get_instance_average() {
    local instance="$1"
    aws cloudwatch get-metric-statistics \
        --metric-name CPUUtilization \
        --namespace=AWS/EC2 \
        --statistics=Maximum \
        --dimensions="Name=InstanceId,Value=$instance" \
        --start-time="$(date -v-7d '+%Y-%m-%dT%H:%M:%S.000Z')" \
        --end-time="$(date '+%Y-%m-%dT%H:%M:%S.000Z')" \
        --period=3600 \
        --query='Datapoints[*].[Maximum]' --output=text \
        | awk '{ sum += $1; n++ } END { if (n > 0) print sum / n; }'
}

print_help() {
    local exit_status="$1"
    cat <<EOF
usage: $0 FILTER

Where FILTER is in AWS filter format.
Example: $0 'Name=tag:Group,Values=groupname'
EOF
    exit "$exit_status"
}

main "$@"
