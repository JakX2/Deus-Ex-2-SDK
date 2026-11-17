#!/usr/bin/env python3
"""Reproducible synthetic legacy-vs-current DX2 exporter microbenchmarks.

Usage:
  python tools/benchmark_exporter_hotpaths.py --size 512 --repeats 5

Outputs JSON with per-format wall-clock timing and exact-output equality.
All data is generated locally with a deterministic seed; NO retail game data
is loaded. Benchmark machine/CPU, Python version, and workload matter.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import random
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"map_exporter"))
sys.path.insert(0,str(ROOT/"tests"))

import reference_legacy_exporter as legacy
from dx2textures import Texture, rgba_pixels
from dx2level import Builder


def timed(fn,repeats):
    elapsed=[]
    for _ in range(repeats):
        start=time.perf_counter()
        fn()
        elapsed.append((time.perf_counter()-start)*1000.)
    return round(statistics.median(elapsed),3)


def texture_case(fmt,n,rng,repeats):
    count=n*n*4 if fmt in ("BGRA8","BGRX8") else (
        ((n+3)//4)*((n+3)//4)*(8 if fmt=="DXT1" else 16))
    raw=rng.randbytes(count)
    tex=Texture("synthetic",fmt,n,n,0,[(n,n,raw)],"generated")
    baseline=legacy.rgba_pixels(tex)
    candidate=rgba_pixels(tex)
    if candidate!=baseline:
        raise ValueError("Texture bytes differ: "+fmt)
    # Each call creates a fresh output. Median of repeat runs; never assert
    # a performance threshold in CI because it depends on the CPU/runtime.
    old=timed(lambda:legacy.rgba_pixels(tex),repeats)
    new=timed(lambda:rgba_pixels(tex),repeats)
    return {"format":fmt,"dimensions":[n,n],"rgba_match":True,
            "legacy_ms":old,"optimized_ms":new,
            "speedup_x":round(old/new,2) if new else None}


def vector_case(count,rng,repeats):
    vectors=[(rng.uniform(-128,128),rng.uniform(-128,128),
              rng.uniform(-128,128)) for _ in range(count)]
    old_bytes,old_bounds=legacy.vector_bytes_and_bounds(vectors,3)
    builder=Builder({}, {}, {})
    builder.vectors(vectors,3)
    if (bytes(builder.binary)!=old_bytes
        or builder.doc["accessors"][0]["min"]!=old_bounds["min"]
        or builder.doc["accessors"][0]["max"]!=old_bounds["max"]):
        raise ValueError("GLB vector payload/extrema differ")
    def current():
        b=Builder({}, {}, {})
        b.vectors(vectors,3)
    old=timed(lambda:legacy.vector_bytes_and_bounds(vectors,3),repeats)
    new=timed(current,repeats)
    return {"vectors":count,"component_type":"float32","bytes_match":True,
            "bounds_match":True,"legacy_ms":old,"optimized_ms":new,
            "speedup_x":round(old/new,2) if new else None}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size",type=int,default=512,help="Texture width and height (multiples of 4 preferred)")
    ap.add_argument("--vectors",type=int,default=30000)
    ap.add_argument("--repeats",type=int,default=5)
    args=ap.parse_args()
    if not 4<=args.size<=2048 or not 1<=args.repeats<=30 or not 100<=args.vectors<=1000000:
        ap.error("size 4..2048, repeats 1..30, vectors 100..1000000")
    rng=random.Random(20261113)
    textures=[texture_case(fmt,args.size,rng,args.repeats)
              for fmt in ("BGRA8","BGRX8","DXT1","DXT3","DXT5")]
    result={"workload":"synthetic, no DX2 game assets",
            "python":sys.version.split()[0],
            "system":platform.platform(),
            "repeats":args.repeats,
            "statistic":"median wall-clock milliseconds, independently timed",
            "textures":textures,"vectors":vector_case(args.vectors,rng,args.repeats)}
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
