from utils.utils import *
# from utils.lichtenstein import *
from utils.lichtenstein_fixed import three_sat_to_planar_three_sat, build_planar_graph

from utils.planarvc import *
import matplotlib.pyplot as plt

import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *
# from generator.generate_prime import *
from generator.sat_to_graph import *
from generator.convert_graphs_to_txt import *

import pickle
import time
import math
import argparse
import libnum

from pysat.formula import CNF
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

print("Clauses before")
print(clauses)

old_vars = n_vars
old_clauses = n_clauses
old_literals = n_literals

max_degree = None
avg_degree = None

if SIMPLIFYSAT:
  n_vars, n_clauses, clauses, n_literals = simplify_SAT( clauses, n_vars, n_clauses )


threesat_formula, new_variables, new_clauses = transformCNF( n_vars, n_clauses, clauses )

print("Threee sat formula after")
print(threesat_formula)
print(new_variables)
print(new_clauses)


threesat_formula_list = [ v for k,v in threesat_formula.items() ]

print(threesat_formula_list)


bipartite_graph = nx_graph_from_3cnf( threesat_formula, new_variables, new_clauses )

nx.draw(bipartite_graph, with_labels=True)
plt.show()

isplanar = detect_planarity( bipartite_graph )

if isplanar:
  # great!!
  print("Yeah!!")
  pass
else:
  # apply Lichtenstein reduction
  # detect crossing 
  pos = nx.spring_layout( bipartite_graph )
  intersections, crossings = detect_crossings( bipartite_graph, pos )

  print(crossings)

  threesat_formula_list = [ v for k,v in threesat_formula.items() ]

  print(threesat_formula_list)

  # planarcnf, planarnvars, metadata = planarize_crossings_lichtenstein( threesat_formula, new_variables, crossings )

  # planarcnf, planarnvars, planarnclauses = three_sat_to_planar_three_sat( threesat_formula_list, crossings )

  # planarcnf = { idx: clause for idx,clause in enumerate(planarcnf) }

  result = three_sat_to_planar_three_sat(
      threesat_formula_list,
      crossings,
      normalize=True,
  )

  planargraph = build_planar_graph(
      threesat_formula_list,
      crossings,
      normalize=True,
  )


  nx.draw(planargraph, with_labels=True)
  plt.show()

  ## THIS IS NOT SUPPOSED TO BE PLANAR: IT IS THE 3SAT FORMULA WHICH IS PLANAR, NOT THE VARIABLE-CLAUSES INCIDENCE GRAPH
  # planar_graph = nx_graph_from_3cnf( planarcnf, planarnvars, planarnclauses )
  # valid = filter_crossings( planarcnf, crossings )

  # planar_graph = build_planar_graph(planarcnf, valid)

  # is_p, _ = nx.check_planarity( planar_graph )
  # print(f"Planar?: {is_p}")

  # nx.draw(planar_graph, with_labels=True)
  # plt.show()

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
    "old_literals": old_literals,
    "simplified_SAT": SIMPLIFYSAT,
    "SAT": clauses,
    "n_vars": n_vars,
    "n_clauses": n_clauses,
    "n_literals": n_literals,
    "cnf": cnf,
    "max_deg": max_degree,
    "avg_deg": avg_degree,
    "timeSAT": timeSAT,
    "metis_format": lines
  }



if PRINT and not GRAPH:
  # print( f"{p} and {q}" ) >> file
  print( f"#Variables before: {old_vars}") 
  print( f"#Clauses before: {old_clauses}" )
  print( f"#Literals before: {old_literals}" )
  print( f"#Variables after: {n_vars}" )
  print( f"#Clauses after: {n_clauses}" )
  print( f"#Literals after: {n_literals}" )
  print( f"Time to SAT: {timeSAT}" )
  print( f"Max degree: {max_degree}" )
  print( f"Avg degree: {avg_degree}" )
  print( "\n" )
  # file = open( "summary.txt", "a+" )
  # file.write( f"{p}_{q} {old_vars} {old_clauses} {n_vars} {n_clauses} {timeSAT} {max_degree} {avg_degree}\n" )
  # file.close()

elif PRINT and GRAPH:
  print( f"#Variables before: {old_vars}") 
  print( f"#Clauses before: {old_clauses}" )
  print( f"#Literals before: {old_literals}" )
  print( f"#Variables after: {n_vars}" )
  print( f"#Clauses after: {n_clauses}" )
  print( f"#Literals after: {n_literals}" )
  print( f"Time to SAT: {timeSAT}" )
  print( f"Max degree: {max_degree}" )
  print( f"Avg degree: {avg_degree}" )
  print( "\n" )

  nx.draw(G)
  plt.show()

  # Solve the MIS and check if |MIS|==n_clauses
  # model = solve_MIS( easyG )
  # MIS_size = sizeMIS( easyG, model )

  # model.x.pprint()

# Write the info to a file
# with open( f"{TOP_DIR}/generator/graphs/{p}_{q}.pkl", "wb" ) as f:
#   pickle.dump( DICT, f, protocol=pickle.HIGHEST_PROTOCOL )