''' This test file apply the path of reduction passing trhgouh planar with boudned degree 6'''

from utils.utils import *
from utils.sat3_to_vcDelta3 import *
from utils.vcDelta3_to_planarDelta6 import *
from utils.planarDelta6_to_planarDelta3 import *
from utils.planarDelta3_to_udgDelta3 import *

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

# Just apply Unit propagation
if SIMPLIFYSAT:
  n_vars, n_clauses, clauses, n_literals = simplify_SAT( clauses, n_vars, n_clauses )

# Then transform to 3SAT
threecnf, n, m = sat_to_3sat( n_vars, n_clauses, clauses ) 

print("3SAT after unit propagation")
print(threecnf)

occurences = count_occurences( threecnf, n, m )

clausesgraphs = create_subgraph_clauses( threecnf, n, m )

variablesgraphs = create_subgraph_variables( n, occurences )

# First reduction 3SAT <= Node Cover with Bounded degree 3
G = create_full_graph( n, threecnf, variablesgraphs, clausesgraphs )

if not nx.is_planar(G):
  print("Graph is not planar")
  print("We apply the chain of reductions \nVC Delta boudned 3 <= Planar VC Delta boudned 6 <= Planar VC Delta boudned 3 <= UDG")
  # first get a planar graph with boudned degree 6
  
  # crossings( G )
  random_pos = nx.spring_layout( G, k=1, scale=10000 ) # increase a lot distance among nodes

  print(random_pos)

  nx.set_node_attributes(G, random_pos, "pos")

  intersections, crossings = detect_crossings(G, random_pos)


  if G.number_of_nodes() < 1500:
    print("Plotting the graph from 3sat to VC Delta <= 3")
    nx.draw(G, with_labels=True, pos=random_pos)
    plt.show()


  crossingsubgraphs = []

  for i,crossing in enumerate(intersections):
    H = create_subgraph( crossing, i )
    crossingsubgraphs.append( H )

    # nx.draw(H, with_labels=True, pos=nx.get_node_attributes(H, "pos"))

    # print(crossing[0])

    # G.remove_edge( crossing[0][0], crossing[0][1] )
    # G.remove_edge( crossing[1][0], crossing[1][1] )

    # G = nx.union( G, H )

    # coordslist = list(crossing[3].items())

    # G.add_edges_from([
    #   ( coordslist[0][0], "{}_a".format(coordslist[0][0]) ),
    #   ( coordslist[1][0], "{}_a".format(coordslist[1][0]) ),
    #   ( coordslist[2][0], "{}_a".format(coordslist[2][0]) ),
    #   ( coordslist[3][0], "{}_a".format(coordslist[3][0]) )
    # ])
  # print(intersections)

  gadgets = nx.union_all( crossingsubgraphs )
  nx.draw(gadgets, pos=nx.get_node_attributes(gadgets, "pos"))
  plt.show()