# Add-on development notes

Working notes for the add-on built on top of SOTN Ultimate v1.4 (PSP ending
theme, option flags and menus, retranslated track titles; text packs,
narration, subtitles, retranslation and area banners planned).

These are analysis reports written during development. They describe the
state of the source at the time they were written and contain estimates that
later measurements superseded; `analysis/baseline_build.md` and the step
reports hold measured numbers.

## env/
- `setup.sh`: every command used to bring up the build environment on a clean
  Linux container, including the pitfalls of a fresh clone (section 8b is the
  reproducible recipe). Written for a sandbox with an allowlisting proxy; the
  proxy-specific lines are marked.
- `build-env.sh`: the environment wrapper to source before
  `bash mods/sotn-ultimate/tools/build_disc.sh`.

## analysis/
- `source_architecture.md`: where each planned feature hooks into the source,
  constraints (DRA layout, overlay limits), and the design for text packs and
  the proportional font (Addendum A).
- `baseline_build.md`: measured sizes and free space of an unmodified v1.4
  build.
- `step1_report.md`, `step2_report.md`: second flags byte and menus; PSP
  ending theme.
- `test_ending_shortcut.md`: the test-only build that jumps to the final boss.
- `disc_report.md`: verification and contents of the source discs.
- `retranslation_patch_report.md`: reverse engineering of the English
  retranslation of the Japanese version (text encodings, fonts, renderer).
- `credits_comparison.md`: PS1 and PSP staff rolls compared.
