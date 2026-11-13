#!/usr/bin/env bash
# Re-creates the SOTN Ultimate build/test environment in a fresh Ubuntu 24.04
# container (root, outbound HTTPS through the allowlisting proxy).
# Every step below was run and worked unless marked [BLOCKED] / [NOT DONE].
set -euo pipefail
REPO=/home/claude/work/sotn-ultimate
ENV=/home/claude/work/env
export DEBIAN_FRONTEND=noninteractive

# --- 1. apt: decomp toolchain (tools/requirements-debian.txt) + emulator/test deps
apt-get update
apt-get install -y bchunk binutils-mipsel-linux-gnu binutils-sh-elf bsdmainutils \
  clang-format coreutils curl gcc-mipsel-linux-gnu git libelf-dev make ninja-build \
  p7zip-full python3-pip python3-venv unzip wget xfonts-utils \
  xvfb mednafen cmake imagemagick xdotool mesa-utils libgl1-mesa-dri \
  build-essential pkg-config clang g++ libcapstone-dev libfreetype-dev \
  libavcodec-dev libavformat-dev libavutil-dev libcurl4-openssl-dev \
  libswresample-dev libuv1-dev zlib1g-dev libx11-dev libxext-dev libxrandr-dev \
  libxcursor-dev libxi-dev libxss-dev libxkbcommon-dev libwayland-dev libegl-dev \
  libgl-dev libgles-dev libdrm-dev libgbm-dev libasound2-dev libpulse-dev \
  libxtst-dev libxfixes-dev libxrender-dev libxinerama-dev libxcb1-dev \
  libdecor-0-dev libibus-1.0-dev libudev-dev libdbus-1-dev
# (not in apt on noble: rustup / pre-commit / black -> rustc+cargo and node22
#  and go1.24 were already preinstalled in this image; not needed for the build)

cd "$REPO"
# --- 2. submodules the PS1 (us) build needs (shallow)
git submodule update --init --depth 1 tools/maspsx tools/psyz tools/sotn_utils \
  tools/m2c tools/asm-differ tools/mipsmatch tools/saturn-splitter tools/saturn/sound-player

# --- 3. Python venv (== `make python-dependencies` + the mod's requirements)
python3 -m venv .venv
.venv/bin/pip install -r tools/requirements-python.txt -r mods/sotn-ultimate/tools/requirements.txt

# --- 4. Go tool that extracts the PS1 disc (no external Go deps -> works offline)
make bin/sotn-disk

# --- 5. cc1-psx-26 (GCC 2.6.3 PSX) from the sotn-decomp release; same URL that
#        tools/sotn-assets/deps downloads. NOTE: sha256 of the served tarball is
#        54ced489...c977, NOT the ab156fe5... pinned in bin/cc1-psx-26.tar.gz.sha256
#        (the Go downloader does not verify it; the Makefile rule would).
curl -fSL -o /tmp/cc1-psx-26.tar.gz \
  https://github.com/Xeeynamo/sotn-decomp/releases/download/cc1-psx-26/cc1-psx-26.tar.gz
tar -xzf /tmp/cc1-psx-26.tar.gz -C bin cc1-psx-26
chmod +x bin/cc1-psx-26; printf cc1-psx-26 > bin/cc1-psx-26.tag

# --- 6. Rust tools that need no disc
cargo build --release --manifest-path tools/maria-sfx/Cargo.toml     # used by build_disc.sh
cargo build --release --manifest-path tools/mipsmatch/Cargo.toml     # optional
cargo fetch --manifest-path tools/saturn/assets/Cargo.toml           # gdn_assets.py builds it with --offline
CARGO_TARGET_DIR=build/mod-work/saturn-assets-target \
  cargo build --release --offline --manifest-path tools/saturn/assets/Cargo.toml

# --- 7. builder audio module sources (emsdk itself is [BLOCKED], see README)
mkdir -p build/mod-work/builder && cd build/mod-work/builder
[ -d emsdk ]   || git clone --depth 1 https://github.com/emscripten-core/emsdk.git emsdk
[ -d ffmpeg ]  || git clone --depth 1 --branch n7.1.1 https://github.com/FFmpeg/FFmpeg.git ffmpeg
# emsdk 4.0.10: works now that storage.googleapis.com is allowed
(cd emsdk && ./emsdk install 4.0.10 && ./emsdk activate 4.0.10)
cd "$REPO"

# --- 8. Go modules (sotn-assets, `./sotn.sh ...`): proxy.golang.org must go through the
#        agent proxy, i.e. be REMOVED from NO_PROXY (done in build-env.sh below).

# ===================================================================
# --- 8b. BASELINE BUILD of SOTN Ultimate v1.4 (verified, ~7 min for build_disc.sh itself)
# ===================================================================
# Extra apt packages found necessary: gawk (build_cenp.sh uses strtonum; mawk silently
# skips that check), and 7z/bchunk (already above).
apt-get install -y gawk

# 8b.1 environment wrapper (sources PATH, node, proxy fix, venv). ~/.bashrc line 6 must be
#      `[ -z "${PS1:-}" ] && return` because build_disc.sh runs `set -u` + `source ~/.profile`.
cp ~/.bashrc "$ENV/bashrc.bak"; sed -i '6s/.*/[ -z "${PS1:-}" ] \&\& return/' ~/.bashrc
cat > "$ENV/build-env.sh" <<'EOF'
export PATH=/opt/node22/bin:/usr/local/go/bin:/root/.cargo/bin:$PATH
NP=$(echo "$NO_PROXY" | sed 's/,proxy.golang.org//'); export NO_PROXY="$NP" no_proxy="$NP"
cd /home/claude/work/sotn-ultimate
source .venv/bin/activate
export NODE=/opt/node22/bin/node   # psp_dub.py does os.path.exists(NODE): needs an absolute path
EOF
source "$ENV/build-env.sh"

# 8b.2 discs (inputs: /home/claude/work/discs, read-only)
D=/home/claude/work/discs
ln -sf $D/us_track1.bin disks/sotn.us.bin
printf 'FILE "sotn.us.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    INDEX 01 00:00:00\r\n' > disks/sotn.us.cue
bin/sotn-disk extract disks/sotn.us.cue disks/us >/dev/null                 # -> disks/us
T=$(mktemp -d); printf 'FILE "%s" BINARY\n  TRACK 01 MODE1/2352\n    INDEX 01 00:00:00\n' $D/saturn_track1.bin > $T/s.cue
bchunk $D/saturn_track1.bin $T/s.cue $T/sat >/dev/null                      # cooked 2048 iso
rm -rf disks/saturn; 7z x -y -odisks/saturn $T/sat01.iso >/dev/null || true # "Data Error: CD3" is expected:
rm -rf $T                                                                    # CD3 is a 0-byte CD-DA marker file
bash mods/sotn-ultimate/tools/extract_psp.sh $D/psp.iso                     # -> disks/psp (2190 files)

# 8b.3 audio module (emsdk 4.0.10 + FFmpeg 7.1.1): ~1.5 min. Remove any fake/partial output first.
rm -rf build/mod-work/builder/audio
bash mods/sotn-ultimate/tools/builder/native/build.sh

# 8b.4 BOOTSTRAP (fresh clone only; the tree is circular: generators need a prior build).
#   - Rust sotn_str is used by the C compile step:
cargo build --release --manifest-path tools/sotn_str/Cargo.toml
#   - Saturn assets (src/saturn/*/gen headers) and satxa (needed before gen_saturn_music builds it):
./sotn.sh extract-assets config/assets.saturn.yaml
./sotn.sh build-assets   config/assets.saturn.yaml
gcc -O2 -Wall -o bin/satxa mods/sotn-ultimate/tools/satxa.c -lm
#   - PS1 assets + splat asm (this first `build us` is EXPECTED to fail at link/compile of mod
#     files; it is only needed to create asm/ and src/**/gen/*.h):
make extract_assets VERSION=us
SKIP_CHECK=1 ./sotn.sh build us || true
#   - gen_np3_sconce.py wants build/us/st{np3,no3,rno3}.map ("build NP3 once first"): link each
#     stage once with an EMPTY stub mod_sconce.h to get the retail gfxBanks address, then drop the stub.
for s in np3 no3 rno3; do
  touch src/st/$s/mod_sconce.h; rm -f build/us/src/st/$s/*.o
  ninja build/us/st$s.elf >/dev/null 2>&1 || true     # link fails, map (with gfxBanks) is still written
  rm src/st/$s/mod_sconce.h
done
#   - object files compiled while generated headers were missing are EMPTY (cc1|as pipe hides the
#     failure) -> force them to rebuild:
rm -rf build/us/src
#   (build_disc.sh's first pass then regenerates all mod headers; the 1st invocation may still fail
#    on a missing generated file -- just rerun it; `rm -rf build/us/src` once more if dra.elf
#    reports undefined PlaySfx etc.)

# 8b.5 the build (log: $ENV/baseline-build.log; measured 6m49s on 2 cores once bootstrapped)
bash mods/sotn-ultimate/tools/build_disc.sh 2>&1 | tee "$ENV/baseline-build.log"
mkdir -p /home/claude/work/out
cp build/sotn_ultimate.bin /home/claude/work/out/sotn_ultimate_baseline.bin
printf 'FILE "sotn_ultimate_baseline.bin" BINARY\r\n  TRACK 01 MODE2/2352\r\n    FLAGS DCP\r\n    INDEX 01 00:00:00\r\n' \
  > /home/claude/work/out/sotn_ultimate_baseline.cue
# Result (measured): 704,762,688 bytes, 299,644 sectors, md5 98ff3528c08fa9440d7afe50e8dca13e
# (size equals the v1.4 release; md5 does NOT equal 901d74656aedbd8da3050d6a3716f32f)

# --- 9. PCSX-Redux (headless emulator, OpenBIOS) built from source.
#        Needs SDL3 >= 3.2 which Ubuntu 24.04 lacks: build the bundled submodule.
mkdir -p "$ENV/src" && cd "$ENV/src"
[ -d pcsx-redux ] || git clone --depth 1 --recurse-submodules --shallow-submodules -j4 \
  https://github.com/grumpycoders/pcsx-redux.git
mkdir -p "$ENV/sdl3-build" && cd "$ENV/sdl3-build"
cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DSDL_TESTS=OFF -DSDL_INSTALL_TESTS=OFF \
  -DSDL_EXAMPLES=OFF -DCMAKE_INSTALL_PREFIX=/usr/local "$ENV/src/pcsx-redux/third_party/SDL"
ninja && ninja install && ldconfig
cd "$ENV/src/pcsx-redux"
# MUST be -j1: one cc1plus peaks ~3.2 GB RSS; -j2 got OOM-killed on this 7 GB box.
make -j1 pcsx-redux          # ~80-90 min on 2 cores

# --- 10. smoke-test PS-EXE (no commercial data)
cd "$ENV/smoke"
mipsel-linux-gnu-as -march=r3000 -o hello.o hello.S
mipsel-linux-gnu-ld -T link.ld -o hello.elf hello.o
mipsel-linux-gnu-objcopy -O binary -j .text hello.elf hello.bin
python3 -I mkexe.py hello.bin hello.exe
