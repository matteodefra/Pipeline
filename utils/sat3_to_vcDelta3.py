'''
The following python script implement the reduction of the following paper

Some simplified NP-complete graph problems
M.R. Garey, D.S. Johnson, L. Stockmeyer
https://www.sciencedirect.com/science/article/pii/0304397576900591

where they provide a reduction from 3SAT to Node Cover with bounded degree of 3
'''
import networkx as nx
import itertools

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
  

def sat_to_3sat( n_vars, n_clauses, clauses, desiredK = 3 ):
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

    elif len(vars) < desiredK:
      # augment the clause itself with the same literal
      lit = vars[0]
      while len(clauses[idx]) != desiredK:
        clauses[idx].append( lit )

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



def count_occurences( cnf3, n, m ):
  '''
    Returns a dictionary indexed by the variable and the number of its occurences m(i) (either appearing as x_i or not x_i)
  '''
  occurences = { i:0 for i in range(1,n+1) }

  for k,v in cnf3.items():
    for l in v:
      occurences[abs(l)] += 1

  return occurences



def create_subgraph_variables( n, occurences ):

  Hs = {}

  for i in range(1, n+1):
    H_i = nx.Graph()
    m_i = occurences[i]

    H_i.add_nodes_from( ["T_{},{}".format(i,j) for j in range(1,m_i+1)] )
    H_i.add_nodes_from( ["F_{},{}".format(i,j) for j in range(1,m_i+1)] )

    for j in range(1,m_i+1):
      H_i.add_edge( "T_{},{}".format(i,j), "F_{},{}".format(i,j) )

    for j in range(1,m_i):
      H_i.add_edge( "F_{},{}".format(i,j), "T_{},{}".format(i,j+1) )

    H_i.add_edge("F_{},{}".format(i,m_i), "T_{},{}".format(i,1))

    Hs[i] = H_i

  return Hs


def create_subgraph_clauses( cnf3, n, m ):

  Hprimes = {}

  for k,v in cnf3.items():
    Hprime_i = nx.Graph()

    # Hprime_i.add_nodes_from( [ "V_{},{}".format(k, vi) for vi in v ] )
    Hprime_i.add_nodes_from( [ "V_{},{}".format(k, vi) for vi in range(1,4) ] )
    Hprime_i.add_edges_from( itertools.combinations( Hprime_i.nodes, 2 ) )

    Hprimes[k] = Hprime_i

  return Hprimes



def create_full_graph( n, cnf3, variablegraphs, clausegraphs ) -> nx.Graph:

  occurences = { i:0 for i in range(1,n+1) }

  edgesetB1 = []
  edgesetB2 = []

  for k,v in cnf3.items():
    for index,l in enumerate(v):
      occurences[abs(l)] += 1

      jth = occurences[abs(l)]

      if l < 0:
        # negative occurence
        edgesetB2.append( ( "F_{},{}".format(abs(l), jth), "V_{},{}".format(k, index+1) ) )
      else:
        # negative occurence
        edgesetB1.append( ( "T_{},{}".format(abs(l), jth), "V_{},{}".format(k, index+1) ) )

  graphs = []
  for _,Gv in variablegraphs.items():
    graphs.append(Gv)
  for _,Gc in clausegraphs.items():
    graphs.append(Gc) 

  G = nx.union_all( graphs )

  G.add_edges_from( edgesetB1 )
  G.add_edges_from( edgesetB2 )

  return G