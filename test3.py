from utils.utils import *
from utils.sat3_to_vcDelta3 import *
from utils.orthogonal_drawing import *
from utils.planarDelta3_to_udgDelta3 import *

import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *

import argparse
import math
import matplotlib.pyplot as plt


from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.process import Processor

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
print(f"Num variables: {n_vars}")
print(f"Num clauses: {n_clauses}")
print(f"Num literals: {n_literals}")

threecnf, n, m = sat_to_3sat( n_vars, n_clauses, clauses ) 

## SIMPLIFY SAT FORMULA USING PREPROCESS
# Create the CNF for PySat
cnf = CNF( from_clauses=[v for _,v in threecnf.items()] )

cnf.to_file("temp.cnf")

import subprocess

result = subprocess.run(
    ["bash", "bashcadical.sh"],
    capture_output=True,
    text=True
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)

# processor = Processor(bootstrap_with=cnf)

# processed = processor.process()

# print(processed.clauses)
# print(processed.status)

# with Solver(bootstrap_with=processed) as solver:
#   solver.solve()

# print('proc model:', solver.get_model())

# print('orig model:', processor.restore(solver.get_model()))

# processor.delete()