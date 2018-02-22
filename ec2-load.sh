#!/usr/bin/env bash

set -eu

main() {
    read_args "$@"
    [ -n "${filters:-}" ] || print_help "$?"

    local instances=($(filters_instances "${filters[@]}"))
    get_output_for_humans "${instances[@]}" | sort -k2,2 -n
}

read_args() {
    while [ "${#}" -gt 0 ]; do
        case "${1}" in
            -f|--filters|--filters=*)
                if [ "${1#*=}" = "$1" ]; then
                    shift
                    while [ "${#}" -gt 0 ]; do
                        case "${1}" in
                            -*)
                                break
                                ;;
                            *)
                                filters+=("$1")
                                shift
                                ;;
                        esac
                    done
                else
                    filters+=("${1#*=}")
                    shift
                fi
                ;;
            --profile|--profile=*)
                if [ "${1#*=}" = "$1" ]; then
                    param="$2"
                    shift
                else
                    param="${1#*=}"
                fi
                [ -z "${param:-}" ] && print_help 1
                export AWS_PROFILE="$param"
                shift
                ;;
            -h|--help)
                print_help 0
                ;;
            *)
                print_help 1
        esac
    done
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

filters_instances() {
    local filters=("$@")
    aws ec2 describe-instances \
        --filters "${filters[@]}" 'Name=instance-state-code,Values=16' \
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
usage: $0 [-f,--filters FILTERS] [--profile AWS_PROFILE]

Where FILTERS is a list of AWS EC2 filters.
Example: $0 --filters 'Name=tag:Group,Values=groupname' 'Name=tag:Name,Values=name'

And AWS_PROFILE is a boto profile.
EOF
    exit "$exit_status"
}

main "$@"
