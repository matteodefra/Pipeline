
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Hashable, List, Optional, Tuple
import math
import random

import networkx as nx

Point = Tuple[float, float]
OrientedEdge = Tuple[Hashable, Hashable]

@dataclass(frozen=True)
class Crossing:
    id: int
    e1: OrientedEdge
    e2: OrientedEdge
    t1: float
    t2: float
    point: Point

def _line_intersection(a: Point, b: Point, c: Point, d: Point) -> Optional[Tuple[float, float, Point]]:
    bax, bay = b[0] - a[0], b[1] - a[1]
    dcx, dcy = d[0] - c[0], d[1] - c[1]
    cax, cay = c[0] - a[0], c[1] - a[1]
    den = bax * dcy - bay * dcx
    if abs(den) < 1e-12:
        return None
    t = (cax * dcy - cay * dcx) / den
    u = (cax * bay - cay * bax) / den
    p = (a[0] + t * bax, a[1] + t * bay)
    return t, u, p

def _segments_cross_strict(a, b, c, d):
    inter = _line_intersection(a,b,c,d)
    if inter is None:
        return None
    t,u,p = inter
    eps=1e-9
    if eps < t < 1-eps and eps < u < 1-eps:
        return t,u,p
    return None

def _add_gjs_vertex_cover_crossover(G: nx.Graph, gadget_id: int) -> Dict[str, Any]:
    p = lambda name: ("gjs_crossover", gadget_id, name)
    v1, v1p, v2, v2p = p("v1"), p("v1p"), p("v2"), p("v2p")
    a, b, c, d = p("a"), p("b"), p("c"), p("d")
    e, f, g = p("e"), p("f"), p("g")
    h, i = p("h"), p("i")
    j, k, l = p("j"), p("k"), p("l")
    m, n, o, q, r, s = p("m"), p("n"), p("o"), p("q"), p("r"), p("s")
    G.add_nodes_from([v1,v1p,v2,v2p,a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,q,r,s])
    edges = [
        (a,b),(b,c),(c,d),
        (g,h),(h,i),(i,j),
        (a,e),(e,f),(f,g),
        (d,k),(k,l),(l,j),
        (b,h),(c,i),
        (v1,a),(v1,g),
        (v1p,d),(v1p,j),
        (v2,a),(v2,b),(v2,c),(v2,d),
        (v2p,g),(v2p,h),(v2p,i),(v2p,j),
        (e,b),(f,h),(c,k),(i,l),
        (b,m),(m,n),(n,c),
        (h,r),(r,s),(s,i),
        (m,o),(o,r),(n,q),(q,s),
    ]
    G.add_edges_from(edges)
    return {"nodes":{"v1":v1,"v1p":v1p,"v2":v2,"v2p":v2p},
            "h_left":v1,"h_right":v1p,"v_top":v2,"v_bottom":v2p}

def crossover_cover_table():
    H=nx.Graph()
    gadget=_add_gjs_vertex_cover_crossover(H,0)
    verts=list(H.nodes())
    E=list(H.edges())
    pair1={gadget["nodes"]["v1"],gadget["nodes"]["v1p"]}
    pair2={gadget["nodes"]["v2"],gadget["nodes"]["v2p"]}
    out={}
    for i in range(3):
        for j in range(3):
            best=math.inf
            for mask in range(1<<len(verts)):
                if mask.bit_count()>=best: continue
                S={verts[t] for t in range(len(verts)) if (mask>>t)&1}
                if len(S&pair1)!=i or len(S&pair2)!=j: continue
                if all(u in S or v in S for u,v in E):
                    best=mask.bit_count()
            out[(i,j)] = int(best)
    return out

def _random_point_set(n, rng):
    pts=[]; seen=set()
    while len(pts)<n:
        x=rng.random(); y=rng.random()
        key=(round(x,12), round(y,12))
        if key in seen: continue
        seen.add(key); pts.append((x,y))
    return pts

def _find_crossings_from_positions(G, pos):
    edges=list(G.edges())
    crossings=[]; crossing_points=[]
    for i,(u1,v1) in enumerate(edges):
        a,b=pos[u1],pos[v1]
        for j in range(i+1,len(edges)):
            u2,v2=edges[j]
            if len({u1,v1,u2,v2})<4: continue
            c,d=pos[u2],pos[v2]
            inter=_segments_cross_strict(a,b,c,d)
            if inter is None: continue
            t1,t2,p=inter
            for q in crossing_points:
                if (p[0]-q[0])**2 + (p[1]-q[1])**2 < 1e-12:
                    return None
            crossing_points.append(p)
            crossings.append(Crossing(len(crossings),(u1,v1),(u2,v2),t1,t2,p))
    return crossings

def _generic_straight_line_embedding(G, seed=0, max_attempts=200):
    nodes=list(G.nodes())
    for attempt in range(max_attempts):
        rng=random.Random(hash((seed,attempt)))
        pos=dict(zip(nodes,_random_point_set(len(nodes),rng)))
        crossings=_find_crossings_from_positions(G,pos)
        if crossings is not None:
            return pos,crossings
    raise RuntimeError("failed generic embedding")

def reduce_vertex_cover_to_planar_vertex_cover(G,k=None,seed=0,max_embedding_attempts=200,verify_planarity=True):
    pos,crossings = _generic_straight_line_embedding(G,seed,max_embedding_attempts)
    Gp=nx.Graph(); Gp.add_nodes_from(G.nodes())
    edge_crossings={e:[] for e in G.edges()}
    gadget_records={}
    for cr in crossings:
        gadget=_add_gjs_vertex_cover_crossover(Gp,cr.id)
        gadget_records[cr.id]={"crossing":cr,"gadget":gadget}
        edge_crossings[cr.e1].append((cr.t1,(gadget["h_left"],gadget["h_right"]),cr.id))
        edge_crossings[cr.e2].append((cr.t2,(gadget["v_top"],gadget["v_bottom"]),cr.id))
    for (u,v) in G.edges():
        seq=sorted(edge_crossings[(u,v)], key=lambda x:x[0])
        if not seq:
            Gp.add_edge(u,v); continue
        Gp.add_edge(u, seq[0][1][0])
        for idx in range(len(seq)-1):
            Gp.add_edge(seq[idx][1][1], seq[idx+1][1][0])
        Gp.add_edge(seq[-1][1][1], v)
    if verify_planarity:
        ok,_=nx.check_planarity(Gp)
        assert ok
    return Gp, (None if k is None else k+13*len(crossings)), {"crossings":len(crossings),"positions":pos,"max_degree":max(dict(Gp.degree()).values(), default=0)}

