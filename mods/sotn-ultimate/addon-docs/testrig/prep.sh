#!/bin/bash
# usage: prep.sh <image.cue> <ExecutionMode>  -> boots to the file select screen
export DISPLAY=:7 HOME=/home/claude/ds/home XDG_RUNTIME_DIR=/tmp/xdg
B=/home/claude/emu/squashfs-root/usr/bin; K=/home/claude/ds/k.sh
pkill -f duckstation-qt; sleep 2; rm -f $B/duckstation.log
sed -i "s/^ExecutionMode = .*/ExecutionMode = $2/" $B/settings.ini
cd $B && (./duckstation-qt -batch "$1" > /tmp/ds.out 2>&1 &)
for i in $(seq 1 90); do sleep 1; grep -q "Setloc     53:0" $B/duckstation.log 2>/dev/null && break; done
sleep 6; $K Return 0.15 6; $K x 0.15 10
