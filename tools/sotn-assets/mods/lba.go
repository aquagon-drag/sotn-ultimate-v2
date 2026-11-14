package mods

import (
	"fmt"
	"io"
	"strings"

	"github.com/xeeynamo/sotn-decomp/tools/sotn-disk/iso9660"
)

const (
	lbaOffset = 0 // sector offset
	lbaSize   = 1 // file size
)

type lbaEntry struct {
	Define   string
	FilePath string
	Mode     int
}

// stagePrefix returns "BOSS" for boss/MAR stages, "ST" otherwise.
func stagePrefix(stage string) string {
	if strings.HasPrefix(stage, "BO") ||
		strings.HasPrefix(stage, "RBO") ||
		stage == "MAR" {
		return "BOSS"
	}
	return "ST"
}

// stageSoundPrefix returns "SD_Z" for reverse stages with 4-char names, "SD_ZK" otherwise.
func stageSoundPrefix(stage string) string {
	if stage[0] == 'R' && len(stage) == 4 {
		return "SD_Z"
	}
	return "SD_ZK"
}

// stageFilePath returns the ISO path for a stage file component.
func stageFilePath(stage, filename string) string {
	return fmt.Sprintf("%s/%s/%s", stagePrefix(stage), stage, filename)
}

// stageEntries returns the 6 lbaEntry items for a single stage.
func stageEntries(stage string) []lbaEntry {
	prefix := strings.ToUpper(stagePrefix(stage))
	sound := stageSoundPrefix(stage)
	return []lbaEntry{
		{fmt.Sprintf("%s_%s_F_BIN_OFF", prefix, stage), stageFilePath(stage, fmt.Sprintf("F_%s.BIN", stage)), lbaOffset},
		{fmt.Sprintf("%s_%s_BIN_OFF", prefix, stage), stageFilePath(stage, fmt.Sprintf("%s.BIN", stage)), lbaOffset},
		{fmt.Sprintf("%s_%s_BIN_LEN", prefix, stage), stageFilePath(stage, fmt.Sprintf("%s.BIN", stage)), lbaSize},
		{fmt.Sprintf("%s_%s_VH_OFF", prefix, stage), stageFilePath(stage, fmt.Sprintf("%s%s.VH", sound, stage)), lbaOffset},
		{fmt.Sprintf("%s_%s_VH_LEN", prefix, stage), stageFilePath(stage, fmt.Sprintf("%s%s.VH", sound, stage)), lbaSize},
		{fmt.Sprintf("%s_%s_VB_LEN", prefix, stage), stageFilePath(stage, fmt.Sprintf("%s%s.VB", sound, stage)), lbaSize},
	}
}

var uniqueStages = []string{
	"NO0", "NO1", "LIB", "CAT", "NO2", "CHI", "DAI", "NP3",
	"CEN", "NO4", "ARE", "TOP", "NZ0", "NZ1", "WRP",
	"DRE",
	"ST0",
	"RNO0", "RNO1", "RLIB", "RCAT", "RNO2", "RCHI", "RDAI", "RNO3",
	"RCEN", "RNO4", "RARE", "RTOP", "RNZ0", "RNZ1", "RWRP",
	"MAD", "NO3", "SEL",
	"TE1", "TE2", "TE3", "TE4", "TE5",
	"BO7", "MAR", "BO6", "BO5", "BO4", "BO3", "BO2", "BO1", "BO0",
	"RBO8", "RBO7", "RBO6", "RBO5", "RBO4", "RBO3", "RBO2", "RBO1", "RBO0",
}

var miscEntries = []lbaEntry{
	{"OFF_WARNING_TIM", "WARNING.TIM", lbaOffset},
	{"LEN_WARNING_TIM", "WARNING.TIM", lbaSize},
	{"OFF_BIN_FGAME2", "BIN/F_GAME2.BIN", lbaOffset},
	{"OFF_BIN_FGAME", "BIN/F_GAME.BIN", lbaOffset},
	{"OFF_SD_XA_STR1", "SD/XA_STR1.", lbaOffset},
	// Saturn port mod: the new weapons 60-63 (mods/sotn-ultimate/tools/build_saturn_weapons.sh)
	{"OFF_BIN_WEAPON2", "BIN/WEAPON2.BIN", lbaOffset},
	// Saturn port mod: Richter's alternate costume (mods/sotn-ultimate/tools/build_ric2.py)
	{"OFF_BIN_RIC", "BIN/RIC.BIN", lbaOffset},
	{"OFF_BIN_RIC2", "BIN/RIC2.BIN", lbaOffset},
	// Saturn port mod: boss Richter in the coat (mods/sotn-ultimate/tools/build_bo6ric2.py)
	{"OFF_BIN_BO6RIC2", "BIN/BO6RIC2.BIN", lbaOffset},
	// Saturn port mod: Richter in the coat in the endings (mods/sotn-ultimate/tools/build_selric2.py)
	{"OFF_BIN_SELRIC2", "BIN/SELRIC2.BIN", lbaOffset},
	// Saturn port mod: the Saturn's playable Maria (mods/sotn-ultimate/tools/build_mar.sh)
	{"OFF_BIN_MARIA", "BIN/MARIA.BIN", lbaOffset},
	{"LEN_BIN_MARIA", "BIN/MARIA.BIN", lbaSize},
	// Saturn port mod: her Saturn voice and sounds (mods/sotn-ultimate/tools/gen_mar_sounds.py)
	{"OFF_BIN_MARIA_SD", "BIN/MARIA_SD.BIN", lbaOffset},
	// Saturn port mod: the same with the PSP dub's English clips (gen_mar_sounds.py --psp)
	{"OFF_BIN_MARIA_SD_PSP", "BIN/MARIA_SD_PSP.BIN", lbaOffset},
	// Saturn port mod: her PS1-dub bank (a copy of MARIA_SD_PSP.BIN)
	{"OFF_BIN_MARIA_SD_PS1", "BIN/MARIA_SD_PS1.BIN", lbaOffset},
	// Saturn port mod: the PSP Maria (src/maria; mods/sotn-ultimate/tools/build_mar2.sh)
	{"OFF_BIN_MARIA2", "BIN/MARIA2.BIN", lbaOffset},
	{"LEN_BIN_MARIA2", "BIN/MARIA2.BIN", lbaSize},
	{"OFF_BIN_MARIA2_SD", "BIN/MARIA2_SD.BIN", lbaOffset},
	// Saturn port mod: CEN with the PSP Maria fight (mods/sotn-ultimate/tools/build_cenp.sh)
	{"OFF_BIN_CENP", "BIN/CENP.BIN", lbaOffset},
	{"LEN_BIN_CENP", "BIN/CENP.BIN", lbaSize},
	// Saturn port mod: the PSP dub's player grunts (mods/sotn-ultimate/tools/gen_psp_grunts.py)
	{"OFF_BIN_ALK_PSP", "BIN/ALK_PSP.BIN", lbaOffset},
	{"OFF_BIN_RIH_PSP", "BIN/RIH_PSP.BIN", lbaOffset},
	// Saturn port mod: the PSP dub's stage and familiar sound banks (mods/sotn-ultimate/tools/gen_psp_sfx.py)
	{"OFF_BIN_SFX_PSP", "BIN/SFX_PSP.BIN", lbaOffset},
	// Saturn port mod: the Saturn-only bestiary pictures (mods/sotn-ultimate/tools/build_monster2.py)
	{"OFF_BIN_MONSTER2", "BIN/MONSTER2.BIN", lbaOffset},
	// Saturn port mod: the JP dub's sound banks (mods/sotn-ultimate/tools/gen_jp_sd.py)
	{"OFF_BIN_JP_SD", "BIN/JP_SD.BIN", lbaOffset},
	// Saturn port mod: Alucard's sprites + the System screen's options code (mods/sotn-ultimate/tools/build_sysopt.sh)
	{"OFF_BIN_ARC_F2", "BIN/ARC_F2.BIN", lbaOffset},
	// Saturn port mod: NO3's bank for Richter's / Maria's horse ride (mods/sotn-ultimate/tools/gen_no3_sounds.py)
	{"OFF_BIN_NO3RIDE", "BIN/NO3RIDE.BIN", lbaOffset},
	// SOTN Ultimate add-on: the retranslation's text pack, the second to last file on the disc (SD/TXT_PAD.BIN is the last: a read-ahead runway, mods/sotn-ultimate/tools/check_cd_lba.py)
	{"OFF_SD_TXT_RT", "SD/TXT_RT.BIN", lbaOffset},
	{"vab0Len", "SD_J010.VB", lbaSize},
	{"SD_ALK_VH_LEN", "VAB/SD_ALK.VH", lbaSize},
	{"SD_RIH_VH_LEN", "VAB/SD_RIH.VH", lbaSize},
	{"SD_TUKA2_VH_LEN", "SERVANT/SD_BAT.VH", lbaSize},
	{"SD_TUKA1_VH_LEN", "SERVANT/SD_FAIRY.VH", lbaSize},
	{"SD_MAR_VH_LEN", "VAB/SD_MAR.VH", lbaSize},
	{"SD_MAR2_VH_LEN", "SERVANT/SD_GHOST.VH", lbaSize},
	{"SD_MAK_VH_LEN", "SERVANT/SD_SWORD.VH", lbaSize},
	{"SD_KOA1_VH_LEN", "SERVANT/SD_DEVIL.VH", lbaSize},
	{"SD_KOA2_VH_LEN", "SERVANT/SD_DEVI2.VH", lbaSize},
	{"SD_ALK_VB_LEN", "VAB/SD_ALK.VB", lbaSize},
	{"SD_RIH_VB_LEN", "VAB/SD_RIH.VB", lbaSize},
	{"SD_MAR_VB_LEN", "VAB/SD_MAR.VB", lbaSize},
	{"SD_TUKA1_VB_LEN", "SERVANT/SD_FAIRY.VB", lbaSize},
	{"SD_TUKA2_VB_LEN", "SERVANT/SD_BAT.VB", lbaSize},
	{"SD_KOA1_VB_LEN", "SERVANT/SD_DEVIL.VB", lbaSize},
	{"SD_KOA2_VB_LEN", "SERVANT/SD_DEVI2.VB", lbaSize},
	{"SD_MAK_VB_LEN", "SERVANT/SD_SWORD.VB", lbaSize},
}

var seqEntries = []lbaEntry{
	{"OFF_SEQ_LIB_SEQ", "ST/LIB/SEQ_LIB.SEQ", lbaOffset},
	{"SEQ_LIB_SEQ_LEN", "ST/LIB/SEQ_LIB.SEQ", lbaSize},
	{"OFF_SEQ_DAI_SEQ", "ST/DAI/SEQ_DAI.SEQ", lbaOffset},
	{"SEQ_DAI_SEQ_LEN", "ST/DAI/SEQ_DAI.SEQ", lbaSize},
}

func queryEntry(img *iso9660.WritableImage, entry lbaEntry) (uint32, error) {
	name := fmt.Sprintf("%s;1", entry.FilePath)
	switch entry.Mode {
	case lbaOffset:
		return img.GetFileLocation(name)
	case lbaSize:
		return img.GetFileSize(name)
	default:
		return 0, fmt.Errorf("unknown mode %d", entry.Mode)
	}
}

func writeEntries(w io.Writer, entries []lbaEntry, img *iso9660.WritableImage) error {
	for _, entry := range entries {
		val, err := queryEntry(img, entry)
		if err != nil {
			return fmt.Errorf("querying %s (%s): %w", entry.Define, entry.FilePath, err)
		}
		if _, err := fmt.Fprintf(w, "#define %s 0x%X\n", entry.Define, val); err != nil {
			return err
		}
	}
	return nil
}

// GenerateLbaHeader writes a complete include/lba.h to w based on the disk layout in img.
func GenerateLbaHeader(img *iso9660.WritableImage, w io.Writer) error {
	fmt.Fprintln(w, "// SPDX-License-Identifier: AGPL-3.0-or-later")
	fmt.Fprintln(w, "// Auto-generated by: go run ./tools/sotn-assets disk --lba-dry-run")
	fmt.Fprintln(w, "// Do not edit manually.")
	fmt.Fprintln(w, "#ifndef LBA_GEN_H")
	fmt.Fprintln(w, "#define LBA_GEN_H")
	fmt.Fprintln(w)

	if err := writeEntries(w, miscEntries, img); err != nil {
		return err
	}

	fmt.Fprintln(w)
	fmt.Fprintln(w, "#define vab1Len SD_RIH_VB_LEN")
	fmt.Fprintln(w, "#define vab2Len SD_MAK_VB_LEN")
	fmt.Fprintln(w, "#define vab3Len 108048")

	fmt.Fprintln(w)
	if err := writeEntries(w, seqEntries, img); err != nil {
		return err
	}

	for _, stage := range uniqueStages {
		fmt.Fprintln(w)
		entries := stageEntries(stage)
		if err := writeEntries(w, entries, img); err != nil {
			return err
		}
	}

	fmt.Fprintln(w)
	fmt.Fprintln(w, "#endif // LBA_GEN_H")
	return nil
}
