#!/bin/bash
export DISPLAY=:7
W=$(xdotool search --name "Castlevania" | tail -1)
[ -n "$W" ] && xdotool windowfocus $W 2>/dev/null
xdotool keydown $1; sleep ${2:-0.12}; xdotool keyup $1; sleep ${3:-1}
