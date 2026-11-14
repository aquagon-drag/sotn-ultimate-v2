#!/bin/bash
# usage: run.sh <image.cue> <tag> <ExecutionMode> [wait after load]
export DISPLAY=:7 HOME=/home/claude/ds/home XDG_RUNTIME_DIR=/tmp/xdg
B=/home/claude/emu/squashfs-root/usr/bin; K=/home/claude/ds/k.sh
pkill -f duckstation-qt; sleep 2; rm -f $B/duckstation.log
sed -i "s/^ExecutionMode = .*/ExecutionMode = $3/" $B/settings.ini
cd $B && (./duckstation-qt -batch "$1" > /tmp/ds.out 2>&1 &)
for i in $(seq 1 90); do sleep 1; grep -q "Setloc     53:0" $B/duckstation.log 2>/dev/null && break; done
sleep 6; $K Return 0.15 6; $K x 0.15 10; import -window root /tmp/$2_a.png
N=$(wc -l < $B/duckstation.log); $K x 0.15 ${4:-24}; import -window root /tmp/$2_b.png
tail -n +$N $B/duckstation.log | grep -v "Getstat\|PerfMon\|DataSector\|Delaying\|MemoryCard\|Controller\|AsyncReader" | cut -c1-150 > /tmp/$2.log
grep -c . /tmp/$2.log
