import networkx as nx
import numpy as np

import pyomo.environ as pyo
from pyomo.opt import SolverFactory

def create_clauses(cnf):
  '''
    Take a dimacs formatted clause and convert it to a graph
  '''

  infos = cnf.split( "\n" )

  clauses = {}

  n_clause = 0

  for line in infos:
    line = line.strip()
    if line:
      if line[0] == "p":
        vals = line.split(" ")
        n_vars = int(vals[2])
        n_clauses = int(vals[3])
      elif line[0] == "c":
        continue

      else:
        vals = line.split(" ")

        clauses[n_clause] = []
        for var in vals:
          variable = int(var)
          if variable != 0:
            # Let's save the clause
            clauses[n_clause].append( variable )
        n_clause += 1


  return n_vars, n_clauses, clauses


def create_nodes_edges( n_vars, n_clauses, clauses ):
  '''
    Create nodes and edges for the MIS graph based on clauses
  '''

  G = nx.Graph()

  for clause, variables in clauses.items():
    
    for var in variables:
      G.add_node((clause, var))

    len_clause = len(variables)

    for i in range(len_clause):
      for j in range(i+1, len_clause):

        x_i = variables[i]
        x_j = variables[j]

        G.add_edge( (clause,x_i),(clause,x_j) )

  all_vars = list(clauses.values())

  for i in range(n_clauses):
    for j in range(i+1, n_clauses):
      
      clause_i = all_vars[i]
      clause_j = all_vars[j]

      for var_i in clause_i:
        
        for var_j in clause_j:

          if var_i == - var_j:
            # find opposite sign variable
            G.add_edge( (i, var_i),(j, var_j) )    

  # Return an easily formatted graph
  easyG = nx.Graph()

  nodes = list(range(len(G.nodes())))
  nodes_tupl = list(G.nodes())
  edges = []

  for e in list(G.edges()):
    edges.append( ( nodes_tupl.index(e[0]), nodes_tupl.index(e[1]) ) )

  easyG.add_nodes_from( nodes )
  easyG.add_edges_from( edges )

  return G, easyG



def greedyMIS( G ):
  '''
    Apply the greedy MIS to the graph G 
    (always select the node with the minimum degree)
  '''

  minimum = len(G.nodes())
  nodes_min = []

  for (node,val) in enumerate( list(G.degree()) ):
    if val < minimum:
      nodes_min.clear()
      nodes_min.append( node )
      minimum = val
    elif val == minimum:
      nodes_min.append( node )

  print( nodes_min )
  print( minimum )


def solve_MIS( G ):
  '''
    Exact solution of the MIS with the optimization problem formulation:

    max \sum_{i \in V} x_i

    s.t. x_i + x_j \leq 1 \forall (i,j) \in E

         x_i \in \{0,1\}
  '''

  model = pyo.ConcreteModel()

  # Create the set of nodes and edges

  model.V = pyo.Set( initialize = list(G.nodes()) )
  model.E = pyo.Set( initialize = list(G.edges()), within=model.V * model.V )

  model.x = pyo.Var( model.V, within=pyo.Binary, initialize=0 )

  def indep_cons(self, u, v):
    return model.x[u] + model.x[v] <= 1
  model.constraint = pyo.Constraint( model.E, rule=indep_cons )

  model.obj = pyo.Objective( expr=sum( model.x[i] for i in model.V ), sense=pyo.maximize )

  model.pprint()

  opt = SolverFactory('glpk')
  opt.solve(model) 

  return model


def sizeMIS(G, model):
  '''
    Recover the MIS from the optimization problem model
  '''

  MIS_size = 0

  for i in range(len(G.nodes())):
    # Compute the size of the independent set
    # print( i, pyo.value( model.x[i] ) )
    if pyo.value(model.x[i] > 0.5):
      MIS_size += 1

  return MIS_size


# last_var = None

## DA RIVEDERE
# def reduce_clause( vars, desiredK, new_clauses, cur_var ):

  len_vars = len(vars)

  if len_vars == desiredK:
    if len(new_clauses) == 0:
      new_clauses[ 0 ] = vars
    else:
      new_clauses[ len(new_clauses) ] = vars
    # last_var = vars[-1]
    return
  
  else:
    new_vars_one = []
    for i in range(len_vars-2):
      new_vars_one.append( vars[i] )

    new_vars_one.append( cur_var )

    print("New variable to add left")
    print(cur_var)

    print("Left side tree:")
    print(new_vars_one)

    reduce_clause( new_vars_one, desiredK, new_clauses, cur_var + 1 )

    new_vars_two = []
    for i in range( len_vars-1, 1, -1 ):
      new_vars_two.append( vars[i] )

    new_vars_two.append( - cur_var )

    print("New variable to add right")
    print(-cur_var)

    print("Right side tree:")
    print(new_vars_two)

    reduce_clause( new_vars_two, desiredK, new_clauses, cur_var + 1 )
    

def reduce_clause_iter( vars : list, first_var, desiredK = 3 ):

  len_vars = len(vars)
  new_clauses = {}

  first = vars[0:desiredK-1]
  last = vars[-(desiredK-1)::]

  remaining = vars[desiredK-1:-(desiredK-1)]
  # print(first)

  # print(last)

  # print(remaining)

  new_clauses[ 0 ] = first + [ first_var ]
  i=1

  if remaining:
    for var in remaining:

      new_clauses[i] = [ - first_var, var, first_var + 1 ]
      first_var += 1
      i += 1

  new_clauses[i] = [ -first_var ] + last


  return new_clauses, first_var
  


def transformCNF( n_vars, n_clauses, clauses, desiredK = 3 ):
  '''
    Reduces an arbitrary SAT to max 3-SAT formula by 
    splitting clauses with >3 literals
  '''

  clauses_to_split = []

  next_clause_idx = n_clauses
  first_var = n_vars + 1

  for idx, vars in clauses.items():

    if len(vars) > desiredK:
      # We find a clause with more than desiredK variables
      clauses_to_split.append( idx )

  # Now we split all the clauses exceeding the limit desiredK
  for clause_idx in clauses_to_split:

    vars = clauses[clause_idx]
    len_vars = len(vars)
    new_clauses = {}

    # print( "Clause to reduce:" )
    # print( clause_idx, vars )

    new_clauses, first_var = reduce_clause_iter( vars, first_var )

    first_var += 1

    # print( "Decomposed clause:" )
    # print( new_clauses )

    for _,values in new_clauses.items():
      clauses[ next_clause_idx ] = values
      next_clause_idx += 1

  for clause_idx in clauses_to_split:
    del clauses[clause_idx]

  cnf3 = dict(enumerate(clauses.values()))

  # Return the dictionary reenumarated
  return cnf3, first_var-1, len(cnf3)