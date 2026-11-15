#!/usr/bin/env bash
# SOTN Ultimate add-on: source build environment inside WSL (Ubuntu).
# Resumable: every finished step leaves a marker in ~/sotn/.done; rerun after a failure.
# Everything is installed under ~/sotn except the apt packages (step 1, needs sudo once).
set -euo pipefail
WIN="/mnt/c/Users/aquagon/Downloads"
SHARE="$WIN/Castlevania Symphony of the Night (Ultimate v1.4)(JP Script Add-on)"
X="$SHARE/_wsl"; LOG="$X/logs"; mkdir -p "$LOG"
exec > >(tee -a "$LOG/setup.log") 2>&1
ROOT="$HOME/sotn"; REPO="$ROOT/sotn-ultimate-v2"; T="$ROOT/tools"; M="$ROOT/.done"
mkdir -p "$T" "$M"
BRANCH="${BRANCH:-addon/step6f-glyph-overrun-fix}"
US_BIN="$WIN/Castlevania - Symphony of the Night (USA)/Castlevania - Symphony of the Night (USA) (Track 1).bin"
SAT_BIN="$WIN/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (2M)/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (2M)/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (2M) (Track 1).bin"
JPRE_BIN="$WIN/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (v1.2 English Patched)/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (v1.2 English Patched)/Akumajou Dracula X - Gekka no Yasoukyoku (Japan) (v1.2) (Track 1).bin"
PSP_ISO="$WIN/Castlevania_Dracula_X_Chronicles_USA_INTERNAL_READNFO_PSP-pSyPSP/Castlevania_Dracula_X_Chronicles_USA_INTERNAL_READNFO_PSP-pSyPSP.iso"
SUDO=sudo; [ "$(id -u)" = 0 ] && SUDO=
t0=$(date +%s)
run() { # run <marker> <function>
    if [ -f "$M/$1" ]; then echo "== $1: already done"; return 0; fi
    echo; echo "== $1 ($(date +%T), +$(( ($(date +%s)-t0)/60 )) min)"
    "$2"; touch "$M/$1"; echo "== $1: OK"
}
envfile() {
cat > "$ROOT/env.sh" <<EOT
# source me before building (written by _wsl/setup.sh)
export PATH="$T/go/bin:$T/node/bin:\$HOME/.cargo/bin:\$HOME/go/bin:\$PATH"
export NODE="$T/node/bin/node"
cd "$REPO" && [ -f .venv/bin/activate ] && source .venv/bin/activate
EOT
}
s00_info() {
    . /etc/os-release; [ "${VERSION_ID:-}" = 24.04 ] || { echo "This setup needs Ubuntu 24.04 (found: $PRETTY_NAME). Run it with: wsl -d Ubuntu-24.04 bash <this script>"; exit 1; }
    echo "distro: $PRETTY_NAME | cores: $(nproc) | $(free -g | awk '/Mem/{print "RAM " $2 " GB"}') | python: $(python3 --version 2>&1)"
    df -h "$HOME" | tail -1
    for f in "$US_BIN" "$SAT_BIN" "$JPRE_BIN" "$PSP_ISO"; do [ -f "$f" ] || { echo "MISSING DISC FILE: $f"; exit 1; }; done
    echo "disc files: all four found"
}
s01_apt() {
    export DEBIAN_FRONTEND=noninteractive
    $SUDO apt-get update
    $SUDO apt-get install -y bchunk binutils-mipsel-linux-gnu bsdmainutils coreutils curl \
        gcc-mipsel-linux-gnu git libelf-dev make ninja-build p7zip-full python3-pip python3-venv \
        unzip wget xz-utils build-essential pkg-config gawk cmake
    $SUDO apt-get install -y binutils-sh-elf || echo "note: binutils-sh-elf not installed"
    $SUDO apt-get install -y clang-format xfonts-utils || echo "note: clang-format/xfonts-utils not installed"
}
s02_clone() {
    if [ ! -d "$REPO/.git" ]; then git clone --branch "$BRANCH" https://github.com/aquagon-drag/sotn-ultimate-v2 "$REPO"; fi
    cd "$REPO"
    git submodule update --init --depth 1 tools/maspsx tools/psyz tools/sotn_utils \
        tools/m2c tools/asm-differ tools/mipsmatch tools/saturn-splitter tools/saturn/sound-player
}
s03_go() {
    rm -rf "$T/go"; curl -fSL https://go.dev/dl/go1.24.4.linux-amd64.tar.gz | tar -xz -C "$T"
    "$T/go/bin/go" version
}
s04_rust() {
    if [ ! -x "$HOME/.cargo/bin/cargo" ]; then curl -fsSL https://sh.rustup.rs | sh -s -- -y --profile minimal; fi
    "$HOME/.cargo/bin/cargo" --version
}
s05_node() {
    local f; f=$(curl -fsSL https://nodejs.org/dist/latest-v22.x/SHASUMS256.txt | awk '/linux-x64.tar.xz/{print $2}')
    rm -rf "$T/node" "$T"/node-v22*; curl -fSL "https://nodejs.org/dist/latest-v22.x/$f" | tar -xJ -C "$T"
    mv "$T"/node-v22*-linux-x64 "$T/node"; "$T/node/bin/node" --version
}
s06_venv() {
    cd "$REPO"; python3 -m venv .venv
    .venv/bin/pip install -q --upgrade pip
    .venv/bin/pip install -q -r tools/requirements-python.txt -r mods/sotn-ultimate/tools/requirements.txt
}
s07_sotndisk() { source "$ROOT/env.sh"; make bin/sotn-disk; }
s08_cc1() {
    cd "$REPO"; curl -fSL -o /tmp/cc1-psx-26.tar.gz \
        https://github.com/Xeeynamo/sotn-decomp/releases/download/cc1-psx-26/cc1-psx-26.tar.gz
    tar -xzf /tmp/cc1-psx-26.tar.gz -C bin cc1-psx-26; chmod +x bin/cc1-psx-26; printf cc1-psx-26 > bin/cc1-psx-26.tag
}
s09_rusttools() {
    source "$ROOT/env.sh"
    cargo build --release --manifest-path tools/maria-sfx/Cargo.toml
    cargo fetch --manifest-path tools/saturn/assets/Cargo.toml
    CARGO_TARGET_DIR=build/mod-work/saturn-assets-target \
        cargo build --release --offline --manifest-path tools/saturn/assets/Cargo.toml
    cargo build --release --manifest-path tools/sotn_str/Cargo.toml
}
s10_audio() {
    source "$ROOT/env.sh"
    mkdir -p build/mod-work/builder; cd build/mod-work/builder
    [ -d emsdk ]  || git clone --depth 1 https://github.com/emscripten-core/emsdk.git emsdk
    [ -d ffmpeg ] || git clone --depth 1 --branch n7.1.1 https://github.com/FFmpeg/FFmpeg.git ffmpeg
    (cd emsdk && ./emsdk install 4.0.10 && ./emsdk activate 4.0.10)
    cd "$REPO"; rm -rf build/mod-work/builder/audio
    bash mods/sotn-ultimate/tools/builder/native/build.sh
}
s11_discs() {
    source "$ROOT/env.sh"; mkdir -p disks
    ln -sf "$US_BIN" disks/sotn.us.bin
    printf 'FILE "sotn.us.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n' > disks/sotn.us.cue
    bin/sotn-disk extract disks/sotn.us.cue disks/us >/dev/null
    local tmp; tmp=$(mktemp -d)
    printf 'FILE "%s" BINARY\n  TRACK 01 MODE1/2352\n    INDEX 01 00:00:00\n' "$SAT_BIN" > "$tmp/s.cue"
    bchunk "$SAT_BIN" "$tmp/s.cue" "$tmp/sat" >/dev/null
    rm -rf disks/saturn; 7z x -y -odisks/saturn "$tmp/sat01.iso" >/dev/null || true   # "Data Error: CD3" is expected
    rm -rf "$tmp"
    bash mods/sotn-ultimate/tools/extract_psp.sh "$PSP_ISO"
    # patched JP disc: only DRA.BIN is read (SHA-1 checked by text_rt.py)
    mkdir -p disks/jpre
    python3 - "$JPRE_BIN" disks/jpre/DRA.BIN <<'PY'
import struct, sys
f = open(sys.argv[1], 'rb')
def sec(n):
    f.seek(n * 2352); return f.read(2352)[24:24 + 2048]
pvd = sec(16); root = pvd[156:190]
lba, size = struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0]
d = b''.join(sec(lba + i) for i in range((size + 2047) // 2048)); i = 0
while i < len(d):
    l = d[i]
    if l == 0: i = (i // 2048 + 1) * 2048; continue
    r = d[i:i + l]; name = r[33:33 + r[32]].decode('latin1')
    if name.split(';')[0] == 'DRA.BIN':
        e, sz = struct.unpack('<I', r[2:6])[0], struct.unpack('<I', r[10:14])[0]
        open(sys.argv[2], 'wb').write(b''.join(sec(e + k) for k in range((sz + 2047) // 2048))[:sz]); break
    i += l
else: sys.exit('DRA.BIN not found on the patched JP disc')
PY
    echo "3d038c447f75bb705fd39e8744c150959da9208c  disks/jpre/DRA.BIN" | sha1sum -c -
    # and its font page (the 8 px font: gen_rt_font8.py)
    mkdir -p disks/jpre/BIN
    python3 - "$JPRE_BIN" disks/jpre/BIN/F_GAME.BIN <<'PY'
import struct, sys
f = open(sys.argv[1], 'rb')
def sec(n):
    f.seek(n * 2352); return f.read(2352)[24:24 + 2048]
def rd(l, s): return b''.join(sec(l + i) for i in range((s + 2047) // 2048))[:s]
def find(l, s, parts):
    d = rd(l, s); i = 0
    while i < len(d):
        n = d[i]
        if n == 0: i = (i // 2048 + 1) * 2048; continue
        r = d[i:i + n]; name = r[33:33 + r[32]].decode('latin1').split(';')[0]
        e, sz = struct.unpack('<I', r[2:6])[0], struct.unpack('<I', r[10:14])[0]
        if name == parts[0]:
            return rd(e, sz) if len(parts) == 1 else find(e, sz, parts[1:])
        i += n
    sys.exit('not found on the patched JP disc: ' + parts[0])
root = sec(16)[156:190]
open(sys.argv[2], 'wb').write(find(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], ['BIN', 'F_GAME.BIN']))
PY
    echo "01e4a76232a68f2ce8590e73a59711b866c92852  disks/jpre/BIN/F_GAME.BIN" | sha1sum -c -
    # and the Librarian (its RT text: text_rt.py lib_rt)
    mkdir -p disks/jpre/ST/LIB
    python3 - "$JPRE_BIN" disks/jpre/ST/LIB/LIB.BIN <<'PY'
import struct, sys
f = open(sys.argv[1], 'rb')
def sec(n):
    f.seek(n * 2352); return f.read(2352)[24:24 + 2048]
def rd(l, s): return b''.join(sec(l + i) for i in range((s + 2047) // 2048))[:s]
def find(l, s, parts):
    d = rd(l, s); i = 0
    while i < len(d):
        n = d[i]
        if n == 0: i = (i // 2048 + 1) * 2048; continue
        r = d[i:i + n]; name = r[33:33 + r[32]].decode('latin1').split(';')[0]
        e, sz = struct.unpack('<I', r[2:6])[0], struct.unpack('<I', r[10:14])[0]
        if name == parts[0]:
            return rd(e, sz) if len(parts) == 1 else find(e, sz, parts[1:])
        i += n
    sys.exit('not found on the patched JP disc: ' + parts[0])
root = sec(16)[156:190]
open(sys.argv[2], 'wb').write(find(struct.unpack('<I', root[2:6])[0], struct.unpack('<I', root[10:14])[0], ['ST', 'LIB', 'LIB.BIN']))
PY
    echo "e062568618ec1873d3ab75ae2a032c1ae817671c  disks/jpre/ST/LIB/LIB.BIN" | sha1sum -c -
    echo "disks: us $(find disks/us -type f | wc -l) files, saturn $(find disks/saturn -type f | wc -l), psp $(find disks/psp -type f | wc -l)"
}
s12_bootstrap() { # a fresh clone is circular: generators need a prior build (addon-docs/env/setup.sh 8b.4)
    source "$ROOT/env.sh"
    ./sotn.sh extract-assets config/assets.saturn.yaml
    ./sotn.sh build-assets   config/assets.saturn.yaml
    gcc -O2 -Wall -o bin/satxa mods/sotn-ultimate/tools/satxa.c -lm
    # game_mod.h includes this generated header (build_disc.sh makes it; the asset extractor preprocesses dra.h)
    (cd mods/sotn-ultimate/tools && python3 text_packs.py --header)
    make extract_assets VERSION=us
    SKIP_CHECK=1 ./sotn.sh build us || true          # expected to fail; creates asm/ and src/**/gen/*.h
    for s in np3 no3 rno3; do
        touch src/st/$s/mod_sconce.h; rm -f build/us/src/st/$s/*.o
        ninja build/us/st$s.elf >/dev/null 2>&1 || true
        rm -f src/st/$s/mod_sconce.h
    done
    rm -rf build/us/src
}
s13_build() {
    source "$ROOT/env.sh"; local i ok=0
    # first pass on a fresh clone: build_disc.sh's early gen_sel_text_cd.sh --check needs
    # src/dra/mod_xa_music.h, which a later step of the same script generates
    if [ ! -f src/dra/mod_xa_music.h ]; then
        sed '/gen_sel_text_cd.sh --check/d' mods/sotn-ultimate/tools/build_disc.sh > mods/sotn-ultimate/tools/_bootstrap_build_disc.sh
        echo "-- bootstrap pass ($(date +%T))"
        bash mods/sotn-ultimate/tools/_bootstrap_build_disc.sh > "$LOG/build_bootstrap.log" 2>&1 || {
            tail -25 "$LOG/build_bootstrap.log"
            grep -q "undefined" "$LOG/build_bootstrap.log" && rm -rf build/us/src
            bash mods/sotn-ultimate/tools/_bootstrap_build_disc.sh > "$LOG/build_bootstrap2.log" 2>&1 || tail -25 "$LOG/build_bootstrap2.log"; }
    fi
    for i in 1 2 3; do
        echo "-- build_disc.sh, attempt $i ($(date +%T))"
        if bash mods/sotn-ultimate/tools/build_disc.sh > "$LOG/build_attempt$i.log" 2>&1; then ok=1; break; fi
        tail -25 "$LOG/build_attempt$i.log"
        grep -q "undefined" "$LOG/build_attempt$i.log" && rm -rf build/us/src
    done
    [ $ok = 1 ] || { echo "BUILD FAILED three times; logs in _wsl/logs"; exit 1; }
    cp build/sotn_ultimate.bin "$SHARE/_builds/step6f_src_build.bin"
    printf 'FILE "step6f_src_build.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n' > "$SHARE/_builds/step6f_src_build.cue"
    md5sum build/sotn_ultimate.bin; git -C "$REPO" log --oneline -1
}
echo "===== setup started $(date) ====="
run 00_info s00_info; rm -f "$M/00_info"
run 01_apt s01_apt
run 02_clone s02_clone
run 03_go s03_go
run 04_rust s04_rust
run 05_node s05_node
envfile
run 06_venv s06_venv
run 07_sotndisk s07_sotndisk
run 08_cc1 s08_cc1
run 09_rusttools s09_rusttools
run 10_audio s10_audio
run 11_discs s11_discs
run 12_bootstrap s12_bootstrap
run 13_build s13_build
echo; echo "===== ALL DONE $(date), $(( ($(date +%s)-t0)/60 )) min. Next: bash \"$X/runner.sh\" ====="
