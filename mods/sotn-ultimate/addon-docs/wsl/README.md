# Local build environment (WSL, Gerardo's PC) — working since 2026-11-14

- Distro: **Ubuntu 24.04** in WSL (`wsl -d Ubuntu-24.04 …`). Debian 12 (his default distro) does not work: Python 3.11
  (the decomp's gen.py needs 3.12), a cross gcc that defaults to PIE, binutils printing sign-extended 64-bit addresses
  (breaks the mod's checks), and GCC 12 instead of 13 for the files compiled with the modern cross gcc.
- `setup.sh`: one resumable script (markers in `~/sotn/.done`). Installs apt packages (sudo once), clones the repo to
  `~/sotn/sotn-ultimate-v2`, Go/Node under `~/sotn/tools`, Rust via rustup, venv, cc1-psx-26, the audio module, extracts
  the four discs from his Downloads folders, bootstraps a fresh clone and builds. 21 minutes on his machine (20 cores).
  `~/sotn/env.sh` is the environment to source.
- Fresh-clone ordering problems it handles (not in `env/setup.sh`, which predates them):
  `text_packs.py --header` before `make extract_assets` (game_mod.h includes the generated mod_text_rt.h), and a first
  pass of build_disc.sh without its early `gen_sel_text_cd.sh --check` (needs mod_xa_music.h, generated later).
- `runner.sh`: job runner he starts in a window. Claude writes `_wsl/jobs/NNN_name.sh` (through the connected folder);
  the runner runs them one at a time with env.sh sourced, output in `_wsl/logs/NNN_name.log`, exit code in
  `_wsl/jobs/NNN_name.rc`. `_wsl/runner.alive` holds its last heartbeat. A build takes about 6.5 minutes.
- Check of the environment: step 6f built from source = MD5 daee56a4af3fcdb2ff0e9b641b37e5ab, byte-identical to the
  binary-patched image tested by Gerardo (and so the toolchain reproduces the cloud builds).
- Workflow: edit and commit in any clone, push to GitHub, then a job does `git fetch && git checkout <branch> &&
  bash mods/sotn-ultimate/tools/build_disc.sh` and copies `build/sotn_ultimate.bin` to `_builds`.
