#!/usr/bin/env python3
"""Experimental in-memory MOPP axis-bound refit, not a Havok compiler.

Preserve original topology, opcode widths, jumps, base changes, rescale
operands, diagonal splits and terminal IDs. Prove all triangle vertices
satisfy every axis constraint on their original path under the existing
conservative interpreter. No retail file writes or runtime claims.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import math

import inspect_level_mopp_triangle_tree as mopp
from inspect_mopp_bytecode_roundtrip import _decode, inspect_code_roundtrip

MARGIN = 1.0
MAX_STATES = mopp.MAX_INSTRUCTION_STATES


def graph(code, count):
    """Build original instruction states and exact rescale affine transforms."""
    proof = inspect_code_roundtrip(code, count)
    states = {}
    todo = [(0, 0, 1, (0, 0, 0))]
    while todo:
        state = todo.pop()
        if state in states:
            continue
        if len(states) >= MAX_STATES:
            raise ValueError("Refit state budget exceeded")
        pc, base, factor, bias = state
        r = _decode(code, pc)
        op, role, v, end = r['opcode'], r['role'], r['operands'], pc+r['size']
        children = []
        leaf = None
        def child(target, b=base, f=factor, o=bias):
            children.append((target, b, f, o))
        if 1 <= op <= 4:
            s = 1 << op
            if factor*s > 2**40:
                raise ValueError("Refit rescale budget exceeded")
            child(end, f=factor*s, o=tuple((x-y)*s for x,y in zip(bias,v)))
        elif role == 'forward': child(end)
        elif role in ('jump8','jump16'): child(end+v[0])
        elif role in ('addbase8','addbase16'): child(end,b=base+v[0])
        elif role == 'setbase32': child(end,b=v[0])
        elif role == 'split8plus3': child(end); child(end+v[2])
        elif role == 'split8plus2': child(end); child(end+v[1])
        elif role == 'twojump16': child(end+v[2]); child(end+v[3])
        elif role == 'leaf_inline': leaf=base+op-0x30
        elif role == 'leaf_imm': leaf=base+v[0]
        else: raise ValueError("Unknown refit instruction")
        states[state]=(r,tuple(children),leaf)
        todo.extend(children)
    leaves=[v[2] for v in states.values() if v[2] is not None]
    # Reject different rescale contexts for the same symbolic state until
    # independently proven; no missing or duplicated terminal ownership.
    if len(states)!=proof['reachable_instruction_states'] or len(leaves)!=len(set(leaves)) or sorted(leaves)!=mopp.trace_mopp_code(code,count)['reachable_terminal_triangle_ids']:
        raise ValueError("Refit state/leaf graph differs from original tracer")
    return states


def bounds(triangles, origin, states):
    """Aggregate complete subtree extents in root-quantized coordinates."""
    if len(origin)!=4 or not all(math.isfinite(x) for x in origin) or origin[3]<=0:
        raise ValueError("Invalid original refit quantization")
    result={}
    for state in sorted(states, reverse=True):
        _,children,leaf=states[state]
        if leaf is not None:
            v=triangles[leaf]
            if len(v)!=3 or any(len(p)!=3 or not all(math.isfinite(x) and abs(x)<=1e6 for x in p) for p in v):
                raise ValueError("Malformed source refit triangle")
            q=[tuple((x-o)*origin[3]/65536. for x,o in zip(p,origin[:3])) for p in v]
            lo=tuple(min(p[k] for p in q) for k in range(3))
            hi=tuple(max(p[k] for p in q) for k in range(3))
        else:
            if not children: raise ValueError("Empty refit branch")
            b=[result[c] for c in children]
            lo=tuple(min(v[0][k] for v in b) for k in range(3))
            hi=tuple(max(v[1][k] for v in b) for k in range(3))
        result[state]=(lo,hi)
    return result


def requirements(states, box):
    """Intersect operand intervals required by all original path states.

    Strict upper tests require floor(max-margin)+1; inclusive lower tests
    allow floor(min+margin). 24-bit filters use 65536x local coordinates.
    A half split has one shared threshold, so intersect both inequalities.
    """
    intervals={}
    roles={}
    for state,(r,children,_) in states.items():
        pc,_,factor,bias=state
        op=r['opcode']
        def local(child,axis,side):
            return box[child][side][axis]*factor+bias[axis]
        def restrict(offset,width,lower,upper,role):
            key=(pc+offset,width)
            ceiling=(1<<(8*width))-1
            a,b=intervals.get(key,(0,ceiling))
            intervals[key]=(max(a,lower),min(b,upper))
            roles[key]=role
        def upper(q,scale=1): return math.floor((q-MARGIN)*scale)+1
        def lower(q,scale=1): return math.floor((q+MARGIN)*scale)
        if 0x10<=op<=0x12 or 0x23<=op<=0x25:
            axis=op-(0x10 if op<=0x12 else 0x23)
            restrict(1,1,upper(local(children[0],axis,1)),255,'dual_upper')
            restrict(2,1,0,lower(local(children[1],axis,0)),'dual_lower')
        elif 0x20<=op<=0x22:
            axis=op-0x20
            restrict(1,1,upper(local(children[0],axis,1)),lower(local(children[1],axis,0)),'half_split')
        elif 0x26<=op<=0x28 or 0x29<=op<=0x2b:
            width=1 if op<=0x28 else 3
            axis=op-(0x26 if width==1 else 0x29)
            scale=1 if width==1 else 65536
            restrict(1,width,0,lower(local(children[0],axis,0),scale),'filter_lower')
            restrict(1+width,width,upper(local(children[0],axis,1),scale),(1<<(8*width))-1,'filter_upper')
    return intervals,roles


def assess(code, intervals, roles):
    counts=Counter()
    for (at,width),(lo,hi) in intervals.items():
        old=int.from_bytes(code[at:at+width],'big')
        counts['axis_operands']+=1
        if not lo<=old<=hi:
            counts['violated_'+roles[(at,width)]]+=1
            counts['violated_axis_operands']+=1
        if lo>hi:
            counts['infeasible_'+roles[(at,width)]]+=1
            counts['infeasible_axis_operands']+=1
    return counts


def refit_axis_bounds(code, original, candidate, origin):
    """Return candidate code only if source and new complete axis path gates pass."""
    if len(original)!=len(candidate):
        raise ValueError("Refit requires original triangle inventory")
    states=graph(code,len(original))
    source_req,roles=requirements(states,bounds(original,origin,states))
    target_req,_=requirements(states,bounds(candidate,origin,states))
    source=assess(code,source_req,roles)
    before=assess(code,target_req,roles)
    report={'source':dict(source),'candidate_before':dict(before),
            'source_axis_path_coverage':not source['violated_axis_operands'],
            'candidate_axis_path_coverage':False,'original_control_flow_preserved':False,
            'diagonal_operands_preserved':True,'retail_runtime_verified':False,
            'refit_bytes_changed':0,'refit_passed':False}
    if source['violated_axis_operands'] or before['infeasible_axis_operands']:
        return None,report
    out=bytearray(code)
    changes=Counter()
    for (at,width),(lo,hi) in target_req.items():
        old=int.from_bytes(code[at:at+width],'big')
        new=min(max(old,lo),hi)
        if new!=old:
            out[at:at+width]=new.to_bytes(width,'big')
            changes[roles[(at,width)]]+=1
    out=bytes(out)
    if assess(out,target_req,roles)['violated_axis_operands']:
        raise ValueError("Refit operand verification failed")
    # Independently re-decode candidate and verify exact CFG, opcode and
    # all non-spatial operands. The only allowed differences are refit spans.
    new_states=graph(out,len(original))
    if set(states)!=set(new_states) or any((r['opcode'],r['size'],children,leaf)!=(new_states[s][0]['opcode'],new_states[s][0]['size'],new_states[s][1],new_states[s][2]) for s,(r,children,leaf) in states.items()):
        raise ValueError("Refit changed original control flow or terminal ownership")
    restored=bytearray(out)
    for at,width in target_req:
        restored[at:at+width]=code[at:at+width]
    if bytes(restored)!=code:
        raise ValueError("Refit changed non-axis bytes")
    report.update(candidate_axis_path_coverage=True,original_control_flow_preserved=True,
                  refit_passed=True,refit_bytes_changed=sum(a!=b for a,b in zip(code,out)),
                  changed_operand_roles=dict(changes),exact_code_reversal=True)
    return out,report


def diagonal_diagnostics(code, original, candidate, origin):
    """Test original and modified triangle vertices against hypothesized diagonals.

    No diagonal operands are edited, and the formula is not engine verified.
    A source violation is distinguished from a newly introduced violation.
    """
    from inspect_mopp_axis_point_candidates import _diagonal_projection
    states=graph(code,len(original))
    counts=Counter()
    stack=[((0,0,1,(0,0,0)),())]
    visited=set()
    while stack:
        state,path=stack.pop()
        if state in visited:
            raise ValueError("Shared path context not supported by diagonal diagnostic")
        visited.add(state)
        r,children,leaf=states[state]
        op=r['opcode']
        if leaf is not None:
            old_bad=new_bad=False
            for branch,side in path:
                pc,_,factor,bias=branch
                br=states[branch][0]
                if br['opcode']==0x1b:
                    counts['unknown_diagonal_leaf_paths']+=1
                    continue
                threshold=br['operands'][side]
                for a,b in zip(original[leaf],candidate[leaf]):
                    def p(v):
                        q=tuple(((x-o)*origin[3]/65536.)*factor+z for x,o,z in zip(v,origin[:3],bias))
                        return _diagonal_projection(br['opcode'],q)
                    def miss(v):
                        return v>=threshold+MARGIN if side==0 else v<threshold-MARGIN
                    before,after=miss(p(a)),miss(p(b))
                    counts['diagonal_vertex_path_comparisons']+=1
                    counts['source_diagonal_violations']+=int(before)
                    counts['candidate_diagonal_violations']+=int(after)
                    counts['new_diagonal_violations']+=int(after and not before)
                    old_bad|=before
                    new_bad|=after
            counts['source_triangles_with_diagonal_violations']+=int(old_bad)
            counts['candidate_triangles_with_diagonal_violations']+=int(new_bad)
            counts['new_triangles_with_diagonal_violations']+=int(new_bad and not old_bad)
        else:
            for side,c in enumerate(children):
                stack.append((c,path+((state,side),) if 0x13<=op<=0x1c else path))
    return dict(counts)
