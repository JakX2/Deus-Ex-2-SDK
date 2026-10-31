#!/usr/bin/env python3
"""DX2 SDK research v0.26: strictly read-only TriggerScript .ibd bundle probe.

Usage:
  python dx2_script_bundle_probe.py --game-root "C:\\...\\Deus Ex Invisible War\\Content\\DX2"
  python dx2_script_bundle_probe.py --game-root "C:\\...\\Content\\DX2" --script-archive "...\\TriggerScript.zip"

Never writes to the installation. Prints a JSON report to stdout.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
import zipfile

MAGIC = 0xC0000001
ENTRY_SIZE = 0x130
HEADER_SIZE = 0x34
TS_KIND = 21

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def parse_tsd_resources(blob, *, bundle_name):
    if len(blob)<HEADER_SIZE:raise ValueError(f'{bundle_name}: truncated header')
    magic, align, data_start, data_size, maxres, maxpart, nres, nparts = struct.unpack_from('<8I',blob,0)
    if magic!=MAGIC:raise ValueError(f'{bundle_name}: unexpected magic: {magic:#x}')
    if align!=2048 or data_start%align or data_start+data_size!=len(blob):
        raise ValueError(f'{bundle_name}: invalid bundle extent')
    if nres>200000 or nparts>2000000 or HEADER_SIZE+nres*ENTRY_SIZE+nparts*4>data_start:
        raise ValueError(f'{bundle_name}: invalid table extent')
    part_sizes=struct.unpack_from('<'+str(nparts)+'I',blob,HEADER_SIZE+nres*ENTRY_SIZE) if nparts else ()
    resources={}
    count=0
    for idx in range(nres):
        p=HEADER_SIZE+idx*ENTRY_SIZE
        offset,size,pad,first,part_count=struct.unpack_from('<5I',blob,p)
        kind=blob[p+0x28]
        if not (size>0 and offset>=data_start and offset%align==0 and offset+size+pad<=len(blob)
                and (size+pad)%align==0 and first+part_count<=nparts
                and sum(part_sizes[first:first+part_count])==size):
            raise ValueError(f'{bundle_name}: resource #{idx} has invalid layout')
        if kind!=TS_KIND:continue
        name=blob[p+0x29:p+ENTRY_SIZE].split(b'\0',1)[0].decode('latin1')
        if not name:raise ValueError(f'{bundle_name}: empty script name at #{idx}')
        if name.casefold() in resources:raise ValueError(f'{bundle_name}: duplicate {name}')
        resources[name.casefold()]={'name':name,'index':idx,'offset':offset,'size':size,
            'part_sizes':list(part_sizes[first:first+part_count]),
            'table_digest_uninterpreted':blob[p+0x14:p+0x28].hex()}
        count+=1
    return {'bundle':bundle_name,'sha256':sha256(blob),'resource_count':nres,
            'trigger_scripts':count},resources

def inspect(game_root,source_zip=None,script='TS_2098',source_value_offset=186):
    root=Path(game_root)
    if not root.is_dir():raise FileNotFoundError(f'No Content\\DX2 folder: {root}')
    bundles=[root/'Maps'/'Kernel_TSDALL.ibd',root/'Maps'/'m1_hub_penthouse_upper.ibd']
    b_results=[];present=[]
    for path in bundles:
        if not path.is_file():
            b_results.append({'bundle':path.name,'present':False});continue
        data=path.read_bytes()
        details,resources=parse_tsd_resources(data,bundle_name=path.name)
        details['present']=True
        details['target_present']=script.casefold() in resources
        b_results.append(details)
        found=resources.get(script.casefold())
        if found:
            chunk=data[found['offset']:found['offset']+found['size']]
            present.append((path,chunk,found))
    report={'status':'ok','read_only':True,'script':script,'bundle_reports':b_results,
            'script_matches':[], 'source_comparison':None}
    source=None
    if source_zip is not None:
        zpath=Path(source_zip)
        with zipfile.ZipFile(zpath,'r') as z:
            members=[n for n in z.namelist() if n.replace('\\','/').casefold().endswith('/'+script.casefold()+'.tsd')
                     or n.replace('\\','/').casefold()==script.casefold()+'.tsd']
            if len(members)!=1:raise ValueError(f'Expected one {script}.tsd in archive; found {len(members)}')
            source=z.read(members[0]);
            if not source.startswith(b'1FFE2FST') and not source.startswith(b'0FFE2FST'):
                raise ValueError(f'Unrecognized standalone TSD header for {script}')
            report['source_comparison']={'member':members[0], 'source_sha256':sha256(source),
                 'source_length':len(source),'standalone_header_hex':source[:12].hex()}
    for path,chunk,record in present:
        item={'bundle':path.name,'resource':script,'resource_index':record['index'],
              'bundle_data_offset':record['offset'],'resource_size':record['size'],
              'resource_sha256':sha256(chunk),'part_sizes':record['part_sizes'],
              'resource_table_digest_uninterpreted':record['table_digest_uninterpreted']}
        if source is not None:
            payload=source[12:]
            diffs=([{'payload_offset':i,'standalone_byte':a,'bundled_byte':b} for i,(a,b)
                    in enumerate(zip(payload,chunk)) if a!=b] if len(payload)==len(chunk) else [])
            item['comparison_to_standalone']={'payload_length_matches':len(payload)==len(chunk),
                    'different_byte_count':len(diffs) if len(payload)==len(chunk) else None,
                    'differences_first_20':diffs[:20]}
            if (path.name.casefold()=='m1_hub_penthouse_upper.ibd'
                and len(payload)==len(chunk) and source_value_offset+4<=len(source)
                and source_value_offset>=12):
                off=source_value_offset-12
                value=struct.unpack_from('<f',chunk,off)[0]
                item['candidate_delay_float']={'standalone_tsd_value_offset':source_value_offset,
                    'resource_relative_value_offset':off,'bundle_absolute_value_offset':record['offset']+off,
                    'embedded_value':value,
                    'source_value':struct.unpack_from('<f',source,source_value_offset)[0],
                    'match':chunk[off:off+4]==source[source_value_offset:source_value_offset+4]}
        report['script_matches'].append(item)
    return report

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game-root',required=True,help='Installed Content\\DX2 directory')
    ap.add_argument('--script-archive',help='Optional original TriggerScript.zip archive')
    ap.add_argument('--script',default='TS_2098')
    args=ap.parse_args()
    try:
        result=inspect(args.game_root,args.script_archive,args.script)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,zipfile.BadZipFile) as e:
        print(json.dumps({'status':'error','read_only':True,'message':str(e)},indent=2))
        return 1
    return 0

if __name__=='__main__':sys.exit(main())
