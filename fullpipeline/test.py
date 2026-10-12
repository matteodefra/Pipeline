import networkx as nx
from utils.vcDelta3_to_UBG import * 
from utils.factoring_3SAT import *
from utils.sat3_to_vcDelta3 import *

p=3
q=3

sat, _, _ = factoring_to_3sat( p*q )

# print(sat.clauses)

# Generate a test graph with bounded degree <= 3 (e.g., a Petersen Graph)
# G = create_full_graph( sat.num_vars, sat.clauses,  )

n = sat.num_vars
m = len(sat.clauses)

cnf3 = { i: v for i,v in enumerate(sat.clauses) }

occ        = count_occurences(cnf3, n, m)
G = create_full_graph(n, cnf3,
                 create_subgraph_variables(n, occ),
                 create_subgraph_clauses(cnf3, n, m))

print(f"SAT variables and clauses: {n} and {m}")
print(f"Graph vertices and edges: {G.number_of_nodes()} and {G.number_of_edges()}")


# v_coords, aux_coords, edge_list = create_3d_ogd_ubg(G, S=3)

# print(f"Original Vertices: {len(v_coords)}")
# print(f"Auxiliary Vertices (UBG intermediate nodes): {len(aux_coords)}")
# print(f"Total UBG Edges Generated: {len(edge_list)}")

# To view the coordinates of original node 0:
