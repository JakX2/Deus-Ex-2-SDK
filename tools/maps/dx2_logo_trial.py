#!/usr/bin/env python3
"""Prepare an isolated two-color DX2 logo experiment from the user's own IBDs.

The pinned source version is the user's Maps code.zip. No original files are
included. This creates only candidate files and a receipt; it never installs
them into the game. Use a separate disposable game copy for runtime tests.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil

from dx2_texture_writer import write_candidate
from dx2_ibd_integrity import read_bounded, sha256

TARGET = "meta_iwlogo"
TRIALS = (
    ("A_MainMenu_Magenta", "MainMenu_GFXALL.ibd", "magenta",
     "fb4396bb01a749b6dd1fc2b0faf2c57973f44a44b4293f624b969bd1e36bc76f"),
    ("B_Kernel_Cyan", "Kernel_GFXALL.ibd", "cyan",
     "839416042e6c38a115d597dc50be6e52d0754b35c5bc67a8981a91ba9d9863ec"),
)


def prepare(maps_dir, output, *, trials=TRIALS):
    maps_dir = Path(maps_dir)
    output = Path(output)
    if maps_dir.is_symlink() or output.is_symlink():
        raise ValueError("Symlink maps directory or output refused")
    maps_dir = maps_dir.resolve(strict=True)
    output = output.resolve()
    if (not maps_dir.is_dir() or output.exists() or maps_dir == output or
            maps_dir in output.parents or output in maps_dir.parents):
        raise ValueError("Output must be a new isolated directory outside the source Maps tree")
    sources = []
    # Validate every source before creating any outputs.
    for variant, filename, palette, pin in trials:
        matches = [p for p in maps_dir.iterdir() if p.name.casefold() == filename.casefold()]
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous source bundle: "+filename)
        source = matches[0]
        if sha256(read_bounded(source)) != pin:
            raise ValueError("Source bundle differs from the pinned trial version: "+filename)
        sources.append((variant,source,palette,pin))
    output.mkdir(parents=True,exist_ok=False)
    reports = []
    try:
        for variant, source, palette, pin in sources:
            receipt = write_candidate(source,output/variant/source.name,TARGET,pin,palette=palette)
            reports.append({"variant":variant,"filename":source.name,"palette":palette,**receipt})
        # Check both outputs before producing the optional combined test folder.
        combined = output/"C_Both"
        combined.mkdir()
        for report in reports:
            source = output/report["variant"]/report["filename"]
            candidate = combined/report["filename"]
            if sha256(read_bounded(source)) != report["candidate_sha256"]:
                raise ValueError("Prepared candidate changed")
            with candidate.open("xb") as stream:
                stream.write(read_bounded(source))
            if sha256(read_bounded(candidate)) != report["candidate_sha256"]:
                raise ValueError("Combined candidate changed")
        if any(sha256(read_bounded(s)) != pin for _,s,_,pin in sources):
            raise ValueError("Original changed during experiment preparation")
        result = {
            "schema":"DX2-LogoTrial-v1","texture":TARGET,"variants":reports,
            "combined_variant":"C_Both","runtime_verified":False,
            "game_installation_modified":False,
            "instructions":[
                "Close the game. Use a separate disposable complete game installation.",
                "Back up both original IBD files and confirm their hashes.",
                "Test A by replacing only MainMenu_GFXALL.ibd in the disposable Maps folder.",
                "Restore both original files before testing B (Kernel_GFXALL.ibd only).",
                "Restore both files before testing C (both candidate files).",
                "Start the executable from the disposable copy for each test.",
                "Record the observed logo color or lack of change. Restore both originals afterward."
            ],
        }
        with (output/"trial.json").open("x",encoding="utf-8") as stream:
            json.dump(result,stream,indent=2,sort_keys=True)
            stream.write("\n")
    except Exception:
        shutil.rmtree(output)
        raise
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps-dir",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.maps_dir,args.output)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({"status":"refused","reason":str(exc)}))
        return 2


if __name__=="__main__":
    raise SystemExit(main())
