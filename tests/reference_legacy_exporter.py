"""Frozen reference routines from the original map exporter (before perf work).

Only synthetic data goes through this test oracle. Keep these deliberately
unoptimized so equivalence tests and benchmarks measure the old behavior.
"""
from __future__ import annotations

import math
import struct


def _rgb565(v):
    return (((v>>11)&31)*255//31,((v>>5)&63)*255//63,(v&31)*255//31)


def _palette(colorblock,transparent):
    c0,c1,mask=struct.unpack_from('<HHI',colorblock)
    p0=_rgb565(c0);p1=_rgb565(c1)
    if c0>c1 or not transparent:
        p2=tuple((2*a+b)//3 for a,b in zip(p0,p1));p3=tuple((a+2*b)//3 for a,b in zip(p0,p1))
        colors=[(*p0,255),(*p1,255),(*p2,255),(*p3,255)]
    else:
        colors=[(*p0,255),(*p1,255),(*(tuple((a+b)//2 for a,b in zip(p0,p1))),255),(0,0,0,0)]
    return [colors[(mask>>(2*i))&3] for i in range(16)]


def rgba_pixels(tex,face=0):
    w,h,raw=tex.mipmaps[0]
    if tex.faces is not None:
        if not 0<=face<6:raise ValueError('Invalid cubemap face index')
        raw=tex.faces[0][face]
    if w*h>8192*8192:raise ValueError('Image too large')
    if tex.fmt in ('BGRA8','BGRX8'):
        out=bytearray(w*h*4)
        for i in range(w*h):
            b,g,r,a=raw[i*4:i*4+4]
            out[i*4:i*4+4]=bytes((r,g,b,a if tex.fmt=='BGRA8' else 255))
        return w,h,bytes(out)
    block_bytes=8 if tex.fmt=='DXT1' else 16
    out=bytearray(w*h*4)
    for by in range((h+3)//4):
        for bx in range((w+3)//4):
            at=(by*((w+3)//4)+bx)*block_bytes
            block=raw[at:at+block_bytes]
            colors=_palette(block[-8:],tex.fmt=='DXT1')
            if tex.fmt=='DXT3':
                a=struct.unpack_from('<Q',block)[0]
                alphas=[((a>>(4*i))&15)*17 for i in range(16)]
            elif tex.fmt=='DXT5':
                a0,a1=block[:2];bits=int.from_bytes(block[2:8],'little')
                if a0>a1: table=[a0,a1]+[((7-j)*a0+j*a1)//7 for j in range(1,7)]
                else:table=[a0,a1]+[((5-j)*a0+j*a1)//5 for j in range(1,5)]+[0,255]
                alphas=[table[(bits>>(3*i))&7] for i in range(16)]
            else:alphas=None
            for yy in range(4):
                for xx in range(4):
                    x=bx*4+xx;y=by*4+yy
                    if x>=w or y>=h:continue
                    i=yy*4+xx
                    r,g,b,aa=colors[i]
                    out[4*(y*w+x):4*(y*w+x)+4]=bytes((r,g,b,alphas[i] if alphas is not None else aa))
    return w,h,bytes(out)


def vector_bytes_and_bounds(vectors,width,typ='VEC3'):
    if not vectors:raise ValueError('Empty vertices')
    if any(len(vec)!=width or any(not math.isfinite(float(x)) for x in vec) for vec in vectors):
        raise ValueError('Invalid vertex data')
    packed=struct.pack('<'+str(len(vectors)*width)+'f',
                       *(float(x) for vec in vectors for x in vec))
    bounds=None
    if typ=='VEC3':
        bounds={'min':[min(x[i] for x in vectors) for i in range(3)],
                'max':[max(x[i] for x in vectors) for i in range(3)]}
    return packed,bounds
