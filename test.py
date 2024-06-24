import networkx as nx

import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *
from generator.generate_prime import *
from generator.sat_to_graph import *
from generator.convert_graphs_to_txt import *

import pickle
import time
import math
import argparse

from pysat.formula import CNF
from pysat.solvers import Solver

parser = argparse.ArgumentParser("parser")
parser.add_argument("-g", "--graph", help="1 if want to compute the graph, 0 otherwise", type=int)
parser.add_argument("-s", "--sat", help="1 if want to solve SAT, 0 otherwise", type=int)
parser.add_argument("-d", "--debug", help="1 if want to print a ton of infos, 0 otherwise", type=int)
parser.add_argument("-f", "--simplified", help="1 if want to simplify SAT, 0 otherwise", type=int)
parser.add_argument("-p", "--p", help="prime p", type=int)
parser.add_argument("-q", "--q", help="prime q", type=int)
args = parser.parse_args()

GRAPH = True if args.graph == 1 else False
SOLVESAT = True if args.sat == 1 else False
PRINT = True if args.debug == 1 else False
SIMPLIFYSAT = True if args.simplified == 1 else False

DICT = {}

p = int(args.p)
q = int(args.q)

print( f"Primes: {p} and {q}" )

p_BITS = int(math.log2(p)) + 1
q_BITS = int(math.log2(q)) + 1

# cnf = generate_instance_known_factors( p, q )
cnf = generate_instance( p*q, p_BITS, q_BITS )

n_vars, n_clauses, clauses = create_clauses( cnf )

old_vars = n_vars
old_clauses = n_clauses


if SIMPLIFYSAT:
  n_vars, n_clauses, clauses = simplify_SAT( clauses, n_vars, n_clauses )

if SOLVESAT:
  # Create the CNF for PySat
  clauses_list = []
  for _,v in clauses.items():
    clauses_list.append( v )

  s = 0
  for _,v in clauses.items():
    s += len(v)

  cnf_pysat = CNF( from_clauses=clauses_list )

  # create a SAT solver for this formula:
  with Solver(bootstrap_with=cnf_pysat) as solver:

    start = time.time()

    # 1.1 call the solver for this formula:
    res = solver.solve()

    end = time.time()

    timeSAT = end-start

    # # Get all the models
    # for m in solver.enum_models():
    #   print("Solution")
    #   # print(m)


if GRAPH:
  # CREATE Graph
  G, easyG = create_nodes_edges( n_vars, n_clauses, clauses )

  if easyG.number_of_nodes() != 0:
    max_degree = max( [ val for (node,val) in easyG.degree() ] )
    avg_degree = sum( val for (_,val) in easyG.degree() ) / easyG.number_of_nodes()
  else:
    max_degree = None
    avg_degree = None


  # greedyMIS( G )
  lines = convert_graph( p, q, easyG )

  # Let's save graphs
  DICT[(p,q)] = {
    "G": G,
    "easyG": easyG,
    "old_vars": old_vars,
    "old_clauses": old_clauses,
    "simplified_SAT": SIMPLIFYSAT,
    "SAT": clauses,
    "n_vars": n_vars,
    "n_clauses": n_clauses,
    "cnf": cnf,
    "max_deg": max_degree,
    "avg_deg": avg_degree,
    "timeSAT": timeSAT,
    "metis_format": lines
  }

  # file = open( "summary.txt", "a+" )
  # file.write( f"{p}_{q} {old_vars} {old_clauses} {n_vars} {n_clauses} {timeSAT} {max_degree} {avg_degree}\n" )
  # file.close()

  if PRINT:
    # print( f"{p} and {q}" ) >> file
    print( f"#Variables before: {old_vars}") 
    print( f"#Clauses before: {old_clauses}" )
    print( f"#Variables after: {n_vars}" )
    print( f"#Clauses after: {n_clauses}" )
    print( f"Time to SAT: {timeSAT}" )
    print( f"Max degree: {max_degree}" )
    print( f"Avg degree: {avg_degree}" )
    print( "\n" )

  # Solve the MIS and check if |MIS|==n_clauses
  # model = solve_MIS( easyG )
  # MIS_size = sizeMIS( easyG, model )

  # model.x.pprint()

# Write the info to a file
with open( f"{TOP_DIR}/generator/graphs/{p}_{q}.pkl", "wb" ) as f:
  pickle.dump( DICT, f, protocol=pickle.HIGHEST_PROTOCOL )