"""Bounded in-memory single-operand MOPP rescale rebase experiment.

Preserve the original instruction graph, leaf IDs and root quantization.
Recompute all spatial intervals after changing one local rescale offset.
Uses unverified source-derived diagonal projection hypotheses; no GMP writer.
"""
from collections import Counter
from inspect_mopp_axis_refit import graph, bounds, requirements, assess
from inspect_mopp_diagonal_refit import diagonal_intervals

MAX_TRIALS = 32
MAX_SHIFT = 4


def signature(states):
    result = {}
    for s, (r, children, leaf) in states.items():
        key = s[:2]
        if key in result:
            raise ValueError('Multiple spatial contexts for original instruction')
        result[key] = (r['opcode'], r['size'], tuple(c[:2] for c in children), leaf)
    return result


def intervals(code, triangles, origin):
    states = graph(code, len(triangles))
    req, roles = requirements(states, bounds(triangles, origin, states))
    diagonal, diag_roles = diagonal_intervals(code, triangles, origin)
    if req.keys() & diagonal.keys():
        raise ValueError('Spatial operand spans overlap')
    req.update(diagonal)
    roles.update(diag_roles)
    return states, req, roles


def _rebase_choices(states, req, roles, code):
    """Try nearby ancestor rescale offsets for infeasible axis filters only."""
    parents = {}
    by_pc = {}
    for s, (r, children, _) in states.items():
        if s[0] in by_pc:
            raise ValueError('Shared instruction offset not supported by rebase')
        by_pc[s[0]] = s
        for child in children:
            if child in parents:
                raise ValueError('Shared descendant not supported by rebase')
            parents[child] = s
    choices = set()
    for (at, width), (lo, hi) in req.items():
        if lo <= hi:
            continue
        role = roles[at, width]
        if role not in ('filter_lower', 'filter_upper'):
            continue
        pc = at - (1 if role == 'filter_lower' else 1 + width)
        s = by_pc[pc]
        op = states[s][0]['opcode']
        if not 0x26 <= op <= 0x2b:
            raise ValueError('Infeasible filter operand has wrong opcode')
        axis = op - (0x26 if op <= 0x28 else 0x29)
        depth = 0
        while s in parents:
            s = parents[s]
            depth += 1
            if 1 <= states[s][0]['opcode'] <= 4:
                offset = s[0] + 1 + axis
                for step in range(1, MAX_SHIFT + 1):
                    value = code[offset] + (-step if role == 'filter_lower' else step)
                    if 0 <= value <= 255:
                        choices.add((step, depth, offset, value))
    return sorted(choices)[:MAX_TRIALS]


def rebase_rescale(code, original, candidate, origin):
    """Return an experimental fixed-width code refit or an explicit refusal.

    Only one rescale coordinate byte may change. Original geometry must
    pass the original axis and derived-diagonal paths before any search.
    A successful candidate must pass all paths in the new spatial context.
    """
    if len(original) != len(candidate):
        raise ValueError('Rebase requires unchanged triangle inventory')
    states, req, roles = intervals(code, original, origin)
    sig = signature(states)
    source = assess(code, req, roles)
    report = {'refit_passed': False, 'source_path_coverage': not source['violated_axis_operands'],
              'trial_count': 0, 'rescale_bytes_changed': 0, 'spatial_bytes_changed': 0,
              'projection_hypotheses_runtime_verified': False, 'candidate_code_written': False}
    if source['violated_axis_operands']:
        report['reason'] = 'source_path_violation'
        return None, report
    _, target, target_roles = intervals(code, candidate, origin)
    initial = assess(code, target, target_roles)
    report['initial_infeasible_operands'] = initial['infeasible_axis_operands']
    if not initial['infeasible_axis_operands']:
        report['reason'] = 'rebase_not_required'
        return None, report
    choices = _rebase_choices(states, target, target_roles, code)
    report['bounded_choices'] = len(choices)
    for _, _, at, value in choices:
        report['trial_count'] += 1
        seed = bytearray(code)
        seed[at] = value
        seed = bytes(seed)
        new_states, req, roles = intervals(seed, candidate, origin)
        if signature(new_states) != sig:
            raise ValueError('Rebase changed original control flow')
        if assess(seed, req, roles)['infeasible_axis_operands']:
            continue
        out = bytearray(seed)
        for (offset, width), (lo, hi) in req.items():
            old = int.from_bytes(seed[offset:offset+width], 'big')
            out[offset:offset+width] = min(max(old, lo), hi).to_bytes(width, 'big')
        out = bytes(out)
        final_states, final_req, final_roles = intervals(out, candidate, origin)
        if signature(final_states) != sig or assess(out, final_req, final_roles)['violated_axis_operands']:
            raise ValueError('Rebased candidate fails independent spatial path check')
        restored = bytearray(out)
        restored[at] = code[at]
        for offset, width in req:
            restored[offset:offset+width] = code[offset:offset+width]
        if bytes(restored) != code:
            raise ValueError('Rebase changed unrelated original code bytes')
        report.update(refit_passed=True, rescale_bytes_changed=1,
                      spatial_bytes_changed=sum(a != b for a, b in zip(seed, out)),
                      original_control_flow_preserved=True, exact_code_reversal=True,
                      complete_candidate_path_coverage=True)
        return out, report
    report['reason'] = 'bounded_rebase_search_exhausted'
    return None, report
