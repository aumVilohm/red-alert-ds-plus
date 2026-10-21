#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/red-alert-ds-plus" && pwd)
cd "$base"
if [ ! -r data/REDALERT.MIX ]; then
    printf '%s\n' 'Place REDALERT.MIX from your copy of Red Alert in red-alert-ds-plus/data.' >&2
    exit 1
fi
if [ ! -r data/MAIN.MIX ] && { [ ! -r data/allied/MAIN.MIX ] || [ ! -r data/soviet/MAIN.MIX ]; }; then
    printf '%s\n' 'Place the Allied and Soviet MAIN.MIX files in data/allied and data/soviet, or use MAIN.MIX in data for a single-file installation.' >&2
    exit 1
fi
mkdir -p save
if [ ! -f save/REDALERT.INI ]; then
    cp default.ini save/REDALERT.INI
fi
cat > REDALERT.INI <<EOF
[Paths]
DataPath=$base/data
UserPath=$base/save
EOF
export RED_ALERT_DS_PLUS=1
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/var/run/0-runtime-dir}
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-1}
export SDL_VIDEODRIVER=wayland
export SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS=1
export PULSE_SERVER=${PULSE_SERVER:-unix:$XDG_RUNTIME_DIR/pulse/native}
export PULSE_LATENCY_MSEC=60
mapping='19009b4d4b4800000111000000010000,retrogame_joypad,a:b0,b:b1,x:b2,y:b3,back:b8,guide:b10,start:b9,leftstick:b11,rightstick:b12,leftshoulder:b4,rightshoulder:b5,dpup:b13,dpdown:b14,dpleft:b15,dpright:b16,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:b6,righttrigger:b7,platform:Linux,'
export SDL_GAMECONTROLLERCONFIG="${SDL_GAMECONTROLLERCONFIG:+$SDL_GAMECONTROLLERCONFIG
}$mapping"
chmod u+x ./red-alert-ds-plus
exec ./red-alert-ds-plus > save/run.log 2>&1
