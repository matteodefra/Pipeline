from utils.utils import *
from utils.solve_vc import *
# from utils.sat3_to_vcDelta3 import *
# from utils.planarDelta3_to_udgDelta3 import *
# from utils.vcDelta3_to_unitBallGraph import *

from utils.sat3_to_vcDelta3_2 import *
from utils.vcDelta3_to_unitBallGraph_2 import *
from utils.planarDelta3_to_udgDelta3_2 import *


import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *

import argparse
import math
import matplotlib.pyplot as plt

from pysat.solvers import Solver


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

print("Generated SAT formula from circuit")
# print(clauses)
print(f"Number of vars {n_vars}")
print(f"Number of clauses {n_clauses}")
print(f"Number of literals {n_literals}")

old_vars = n_vars
old_clauses = n_clauses
old_literals = n_literals

max_degree = None
avg_degree = None

# just unit propagation
if SIMPLIFYSAT:
  n_vars, n_clauses, clauses, n_literals = simplify_SAT( clauses, n_vars, n_clauses )

print("SAT formula from circuit after Unit propagation only")
print(f"Number of vars {n_vars}")
print(f"Number of clauses {n_clauses}")
print(f"Number of literals {n_literals}")

# 3sat
cnf3, n, m = sat_to_3sat( n_vars, n_clauses, clauses ) 

print("3SAT formula")
# print(cnf3)
print(f"Number of vars {n}")
print(f"Number of clauses {m}")


occ        = count_occurences(cnf3, n, m)
graph_data = create_full_graph(n, cnf3,
                 create_subgraph_variables(n, occ),
                 create_subgraph_clauses(cnf3, n, m))

print(graph_data.__repr__())

tmp = nx.Graph()
tmp.add_nodes_from(graph_data.nodes)
tmp.add_edges_from(graph_data.edges)

isplanar = nx.is_planar(tmp)

print(f"is planar? {isplanar}")
if isplanar:
  ud_stats = check_and_run( graph_data )

  print(ud_stats)

stats = ubg_stats_only_plain(graph_data)

print(stats)