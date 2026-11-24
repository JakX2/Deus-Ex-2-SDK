"""Experimental diagonal operand refit under source-derived projection hypotheses.

The formulas are NOT runtime verified. Use only with an accepted axis refit,
no native files emitted. Refuse unobserved diagonal opcodes or source failures.
"""
from collections import Counter
import math
from inspect_mopp_axis_refit import graph, assess, MARGIN
from inspect_mopp_axis_point_candidates import _diagonal_projection


def diagonal_intervals(code, triangles, origin):
    states=graph(code,len(triangles))
    intervals={}
    roles={}
    stack=[((0,0,1,(0,0,0)),())]
    visited=set()
    while stack:
        s,path=stack.pop()
        if s in visited:
            raise ValueError("Shared diagonal path context not supported")
        visited.add(s)
        r,children,leaf=states[s]
        op=r['opcode']
        if leaf is None:
            for side,c in enumerate(children):
                stack.append((c,path+((s,side),) if 0x13<=op<=0x1c else path))
            continue
        for branch,side in path:
            pc,_,factor,bias=branch
            opcode=states[branch][0]['opcode']
            if opcode==0x1b:
                raise ValueError("Unknown diagonal opcode cannot be refitted")
            key=(pc+1+side,1)
            a,b=intervals.get(key,(0,255))
            for v in triangles[leaf]:
                q=tuple(((x-o)*origin[3]/65536.)*factor+z for x,o,z in zip(v,origin[:3],bias))
                p=_diagonal_projection(opcode,q)
                if p is None or not math.isfinite(p):
                    raise ValueError("Unverified diagonal projection")
                if side==0:a=max(a,math.floor(p-MARGIN)+1)
                else:b=min(b,math.floor(p+MARGIN))
            intervals[key]=(a,b)
            roles[key]='diagonal_upper' if side==0 else 'diagonal_lower'
    return intervals,roles


def refit_diagonal_bounds(axis_code, original, candidate, origin):
    """Adjust only diagonal split operands; require complete source/target paths."""
    if len(original)!=len(candidate):
        raise ValueError("Diagonal refit requires original triangle inventory")
    source,roles=diagonal_intervals(axis_code,original,origin)
    target,_=diagonal_intervals(axis_code,candidate,origin)
    before=assess(axis_code,target,roles)
    source_counts=assess(axis_code,source,roles)
    report={'source':dict(source_counts),'candidate_before':dict(before),
            'refit_passed':False,'diagonal_refit_bytes_changed':0,
            'projection_hypotheses_runtime_verified':False}
    if source_counts['violated_axis_operands'] or before['infeasible_axis_operands']:
        return None,report
    out=bytearray(axis_code)
    for (at,width),(lo,hi) in target.items():
        old=out[at]
        out[at]=min(max(old,lo),hi)
    out=bytes(out)
    if assess(out,target,roles)['violated_axis_operands']:
        raise ValueError("Diagonal target path verification failed")
    a,b=graph(axis_code,len(original)),graph(out,len(original))
    if set(a)!=set(b) or any((r['opcode'],r['size'],ch,leaf)!=(b[s][0]['opcode'],b[s][0]['size'],b[s][1],b[s][2]) for s,(r,ch,leaf) in a.items()):
        raise ValueError("Diagonal refit changed original graph")
    restored=bytearray(out)
    for at,width in target:
        restored[at:at+width]=axis_code[at:at+width]
    if bytes(restored)!=axis_code:
        raise ValueError("Diagonal refit changed unrelated bytes")
    report.update(refit_passed=True,diagonal_refit_bytes_changed=sum(x!=y for x,y in zip(axis_code,out)),
                  original_control_flow_preserved=True,exact_code_reversal=True)
    return out,report
