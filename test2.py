from utils.utils import *
from utils.sat3_to_vcDelta3 import *
from utils.orthogonal_drawing import *
from utils.planarDelta3_to_udgDelta3 import *
from utils.vcDelta3_to_unitBallGraph import *

import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *

import argparse
import math
import matplotlib.pyplot as plt


parser = argparse.ArgumentParser("parser")
parser.add_argument("-g", "--graph", help="1 if want to compute the graph, 0 otherwise", type=int)
parser.add_argument("-s", "--sat", help="1 if want to solve SAT, 0 otherwise", type=int)
parser.add_argument("-d", "--debug", help="1 if want to print a ton of infos, 0 otherwise", type=int)
parser.add_argument("-f", "--simplified", help="1 if want to simplify SAT, 0 otherwise", type=int)
parser.add_argument("-p", "--p", help="prime p", type=int)
parser.add_argument("-q", "--q", help="prime q", type=int)
parser.add_argument("-b", "--bitnums", help="number of bits", type=int)
args = parser.parse_args()

GRAPH = True if args.graph == 1 else False
SOLVESAT = True if args.sat == 1 else False
PRINT = True if args.debug == 1 else False
SIMPLIFYSAT = True if args.simplified == 1 else False

DICT = {}

b = int(args.bitnums)

if args.p:
  p = int(args.p)
  q = int(args.q)
else:
  _, p, q = generateCompositeNum(b)

print( f"Primes: {p} and {q}" )

p_BITS = int(math.log2(p)) + 1
q_BITS = int(math.log2(q)) + 1

# cnf = generate_instance_known_factors( p, q )
cnf = generate_instance( p*q, p_BITS, q_BITS )

n_vars, n_clauses, clauses, n_literals= create_clauses( cnf )

print("Clauses before")
print(clauses)

old_vars = n_vars
old_clauses = n_clauses
old_literals = n_literals

max_degree = None
avg_degree = None

if SIMPLIFYSAT:
  n_vars, n_clauses, clauses, n_literals = simplify_SAT( clauses, n_vars, n_clauses )


threecnf, n, m = sat_to_3sat( n_vars, n_clauses, clauses ) 

print("Unit propagation")
print(threecnf)

occurences = count_occurences( threecnf, n, m )

clausesgraphs = create_subgraph_clauses( threecnf, n, m )

variablesgraphs = create_subgraph_variables( n, occurences )


G = create_full_graph( n, threecnf, variablesgraphs, clausesgraphs )

print("Plotting the graph from 3sat to VC Delta <= 3")
nx.draw(G)
plt.show()

if not nx.is_planar(G):
  #####
  ## 3D MAPPING
  #####

  # pos3d, edge_routes = orthogonal_3d_draw(G)
  # # pos3d:       {node: (x, y, z)}   — integer grid coordinates
  # # edge_routes: {(u,v): [waypoints]} — axis-aligned polylines

  # ok, conflicts = verify_no_crossings(pos3d, edge_routes)

  # print(ok)
  # print(conflicts)
  # visualize_3d(G, pos3d, edge_routes, title="My Graph")

  # Step 1 — crossing-free 3D orthogonal drawing
  pos3d, edge_routes = orthogonal_3d_draw(G)
  visualize_3d(G, pos3d, edge_routes, title="3D Orthogonal")

  # Step 2 — Unit Ball Graph
  UBG, ubg_pos, original_nodes = build_unit_ball_graph(pos3d, edge_routes)
  ubg_stats(UBG, original_nodes)
  visualize_ubg(UBG, ubg_pos, original_nodes, title="Unit Ball Graph")

else:
  print("Graph is already planar with \Delta <= 3")
  print("Transforming into UDG...")


  H, pos = planar_to_udg(G)

  print(f"UD Graph has {H.number_of_nodes()} nodes and {H.number_of_edges()} edges")

  nx.draw(H, with_labels=True, pos=pos)
  plt.show()