"""Exact original VBSP render-leaf AABBs, fixed-width in-memory synchronization.

The box is the bounds of the owned expanded render polygons, not a convex
spatial-cell or portal box. Empty leaves retain the source all-zero box.
This does not move the splitter planes, portals, navigation or grids.
"""
from collections import Counter
import math
import struct
from inspect_world_position_dependencies import BytePatch


def leaf_boxes(tail,polygons):
    """Derive the complete polygon-range AABB inventory in source leaf order."""
    boxes=[]; seen=set()
    for row in tail['leaves']:
        a,b=row[:2]
        if not 0<=a<=b<=len(polygons):raise ValueError('Invalid leaf polygon range')
        xyz=[]
        for i in range(a,b):
            if i in seen or polygons[i]['polygon']!=i:
                raise ValueError('Invalid leaf polygon identity or ownership')
            seen.add(i)
            v=[x[:3] for x in polygons[i]['vertices']]
            if not v or any(len(x)!=3 or not all(math.isfinite(t) for t in x) for x in v):
                raise ValueError('Invalid leaf polygon positions')
            xyz.extend(v)
        boxes.append(tuple(min(v[k] for v in xyz) for k in range(3))+
                     tuple(max(v[k] for v in xyz) for k in range(3)) if xyz else (0.,)*6)
    if len(seen)!=len(polygons):raise ValueError('Incomplete leaf polygon coverage')
    return boxes


def verify_leaf_boxes(tail,polygons):
    boxes=leaf_boxes(tail,polygons); counts=Counter()
    for row,box in zip(tail['leaves'],boxes):
        if tuple(row[5:11])!=box:raise ValueError('Original leaf AABB differs from owned render geometry')
        counts['vbsp_exact_render_leaf_boxes']+=1
        counts['vbsp_empty_zero_boxes']+=int(row[0]==row[1])
    return dict(counts)


def sync_leaf_boxes(level,tail,original,candidate):
    """Require exact source boxes and unchanged leaf ownership ranges."""
    verify_leaf_boxes(tail,original)
    if len(original)!=len(candidate):raise ValueError('Leaf sync requires original polygon count')
    boxes=leaf_boxes(tail,candidate)
    start=tail['plane_offsets'][0][0]-12-52*len(boxes)
    if not 0<=start<tail['end']:raise ValueError('Invalid source leaf array span')
    patch=BytePatch(level); changed=0
    for i,(row,box) in enumerate(zip(tail['leaves'],boxes)):
        at=start+52*i
        if struct.unpack_from('<5i6f2i',level,at)!=tuple(row):
            raise ValueError('Original VBSP leaf record differs at computed span')
        if tuple(row[5:11])!=box:
            patch.add(at+20,struct.pack('<6f',*box));changed+=1
    out=patch.finish()
    return out,{'vbsp_leaf_bounds_changed':changed,
                'vbsp_leaf_bound_bytes_changed':sum(a!=b for a,b in zip(level,out))}
