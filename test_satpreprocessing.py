from utils.utils import *

import subprocess
import sys
import os
TOP_DIR = os.getcwd()
sys.path.append( TOP_DIR + "/toughsat/" )

from toughsat.factoring import *

import argparse
import math
import matplotlib.pyplot as plt


import pandas as pd 

from pysat.formula import CNF
from pysat.solvers import Solver
from pysat.process import Processor

parser = argparse.ArgumentParser("parser")
parser.add_argument("-p", "--p", help="prime p", type=int)
parser.add_argument("-q", "--q", help="prime q", type=int)
parser.add_argument("-b", "--bitnums", help="number of bits", type=int)
parser.add_argument("-v", "--verbose", help="printing information", type=int, default=0)
parser.add_argument("-t", "--tests", help="number of tests for each bit value", type=int)
args = parser.parse_args()

DICT = {}

b = int(args.bitnums)

numtests = int(args.tests)

column_names = ["t", "bits", "p", "q", "N", "SAT n", "SAT m", "SAT l", \
           "Simplify proc time", "Simplify real time", \
           "SAT proc time", "SAT real time", \
           "SimplSAT n", "SimplSAT m", "SimplSAT l", \
           "SimplSAT proc time", "SimplSAT real time"]
stats = []


for test in range(numtests):

  if args.p:
    p = int(args.p)
    q = int(args.q)
    N = p*q
  else:
    N, p, q = generateCompositeNum(b)

  v = int(args.verbose)

  if v:
    print( f"Primes: {p} and {q}" )

  p_BITS = int(math.log2(p)) + 1
  q_BITS = int(math.log2(q)) + 1

  # cnf = generate_instance_known_factors( p, q )
  circuit_cnf = generate_instance( p*q, p_BITS, q_BITS )

  n, m, sat, n_literals= create_clauses( circuit_cnf )

  # threecnf, n, m = sat_to_3sat( n_vars, n_clauses, clauses ) 

  ## SIMPLIFY SAT FORMULA USING PREPROCESS
  # Create the CNF for PySat
  cnf = CNF( from_clauses=[v for _,v in sat.items()] )

  litscnf = sum( [len(v) for v in cnf.clauses] )

  if v:
    print("SAT formula stats")
    print(f"Num variables: {cnf.nv}")
    print(f"Num clauses: {len(cnf.clauses)}")
    print(f"Num literals: {litscnf}")


  cnf.to_file("temp.cnf")

  if v:
    print("PREPROCESSING ONLY")

  result = subprocess.run(
      ["bash", "bashcadical_prec.sh"],
      capture_output=True,
      text=True
  )

  unknown, totptime, totrtime = read_cadicaloutput( TOP_DIR+"/resprec.txt" )

  if v:
    print(f"status: {unknown}")
    if unknown:
      print(f"Total processing time: {totptime}")
      print(f"Total real time: {totrtime}")

  if not unknown:
    continue

  if v:
    print("SOLVING FROM SCRATCH ORIGINAL SAT")

  result = subprocess.run(
      ["bash", "bashcadicalin.sh"],
      capture_output=True,
      text=True
  )

  solvedoriginal, totorigptime, totorigrtime = read_goodcadicaloutput( TOP_DIR+"/resorig.txt" )

  if v:
    print(f"status: {solvedoriginal}")
    print(f"Total processing time: {totorigptime}")
    print(f"Total real time: {totorigrtime}")


  simplified_cnf = CNF(from_file='out.cnf')  # reading from file
  litssimplifiedcnf = sum( [len(v) for v in simplified_cnf.clauses] )

  if v:
    print("Simplified SAT formula stats")
    print(f"Num variables simplified SAT: {simplified_cnf.nv}")
    print(f"Num clauses simplified SAT: {len(simplified_cnf.clauses)}")
    print(f"Num literals: {litssimplifiedcnf}")

    print("SOLVING FROM SCRATCH SIMPLIFIED SAT")


  result = subprocess.run(
      ["bash", "bashcadicalout.sh"],
      capture_output=True,
      text=True
  )

  solvedsimpl, totpsimpltime, totrsimpltime = read_goodcadicaloutput( TOP_DIR+"/resout.txt" )

  if v:
    print(f"status: {solvedsimpl}")
    print(f"Total processing time: {totpsimpltime}")
    print(f"Total real time: {totrsimpltime}")


  t_stat = [ test, b, p, q, N, cnf.nv, len(cnf.clauses), litscnf, \
             totptime, totrtime, totorigptime, totorigrtime, \
             simplified_cnf.nv, len(simplified_cnf.clauses), litssimplifiedcnf,
             totpsimpltime, totrsimpltime ]
  stats.append( t_stat )



df = pd.DataFrame( stats, columns=column_names)

# goign with 50 steps of preprocessing (apparently they become useless after a while)
df.to_csv( TOP_DIR+"/result/"+f"b={b}_t={numtests}_P=50.csv" )
