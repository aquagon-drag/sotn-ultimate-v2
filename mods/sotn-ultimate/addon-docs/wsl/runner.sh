#!/usr/bin/env bash
# Runs the job scripts Claude puts in _wsl/jobs, one at a time, as your WSL user.
# Output goes to _wsl/logs/<job>.log, the exit code to _wsl/jobs/<job>.rc.
# Stop it with Ctrl+C (or by creating a file named STOP in _wsl). Nothing runs unless this window is open.
X="/mnt/c/Users/aquagon/Downloads/Castlevania Symphony of the Night (Ultimate v1.4)(JP Script Add-on)/_wsl"
J="$X/jobs"; L="$X/logs"; mkdir -p "$J" "$L"
. /etc/os-release; echo "distro: $PRETTY_NAME"; echo "runner started $(date); waiting for jobs in _wsl/jobs (Ctrl+C to stop)"
while :; do
    if [ -f "$X/STOP" ]; then rm -f "$X/STOP" "$X/runner.alive"; echo "stopped"; exit 0; fi
    date +%s > "$X/runner.alive"
    for j in "$J"/*.sh; do
        [ -f "$j" ] || continue
        n=$(basename "$j" .sh); [ -f "$J/$n.rc" ] && continue
        echo "[$(date +%T)] job $n started"
        ( source "$HOME/sotn/env.sh" 2>/dev/null; bash "$j" ) > "$L/$n.log" 2>&1
        echo $? > "$J/$n.rc"
        echo "[$(date +%T)] job $n finished, exit code $(cat "$J/$n.rc")"
    done
    sleep 2
done
