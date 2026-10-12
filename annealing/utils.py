import pickle
import networkx as nx
import os
import random

from qutip import (about, basis, expect, mesolve, qeye, sigmax, sigmay, sigmaz,
                   tensor)


def embed( G ):
  # Embed the nonUD graph instance in a 3D array
  return


def getGraphs():
  # We get the graph instances which are possibly suitable for a 3d version
  # Max degree \Delta <= 6
  with open( f"{os.getcwd()}/generator/graphs/instances.pkl", "rb" ) as f:
    dic = pickle.load( f )

  return dic


def get_random_graph( node_limit_inf: int = 1, node_limit_sup: int = 20 ):
  '''
    # Get a random instance of graph

    we get a random instance which has less than the specified node limit, a.k.a. qubits
  '''
  with open( f"{os.getcwd()}/generator/graphs/instances_simplified.pkl", "rb" ) as f:
    dic = pickle.load( f )

  dic2 = []

  for k,v in dic.items():

    G: nx.Graph = v["easyG"]

    n_nodes = G.number_of_nodes()

    if n_nodes <= node_limit_sup and n_nodes >= node_limit_inf:
      # print(k)
      dic2.append( (k,v) )

  
  # val = random.randint( 0, len(dic2)-1 )
  val = 2

  return dic2[val][0], dic2[val][1]
  # return dic


def get_interactionH( G ):

  N_qubits = G.number_of_nodes()

  n = (sigmaz() + 1) / 2
  x = sigmax()
  I = qeye(2)

  H_interaction = qeye( 2 )
  for i in range(N_qubits-1):
    H_interaction = tensor( H_interaction, I )

  H_interaction = H_interaction - H_interaction

  # print(H_interaction)

  U_ij = 1

  data = [qeye(2)]*N_qubits

  for (e1, e2) in list(G.edges()):
    data_copy = data.copy()

    data_copy[e1] = n
    data_copy[e2] = n

    H_interaction += tensor( data_copy )

  return H_interaction


def get_H_omega( G ):

  N_qubits = G.number_of_nodes()

  n = (sigmaz() + 1) / 2
  x = sigmax()
  I = qeye(2)

  H_Omeg = qeye( 2 )
  for i in range(N_qubits-1):
    H_Omeg = tensor( H_Omeg, I )

  H_Omeg = H_Omeg - H_Omeg

  data = [qeye(2)]*N_qubits

  for i in range( N_qubits ):
    data_copy = data.copy()
    data_copy[i] = x

    H_Omeg += tensor( data_copy )

  return H_Omeg


def get_H_delta( G ):

  N_qubits = G.number_of_nodes()

  n = (sigmaz() + 1) / 2
  z = sigmaz()
  I = qeye(2)

  H_Delt = qeye( 2 )
  for i in range(N_qubits-1):
    H_Delt = tensor( H_Delt, I )

  H_Delt = H_Delt - H_Delt

  data = [qeye(2)]*N_qubits

  for i in range( N_qubits ):
    data_copy = data.copy()
    data_copy[i] = z

    H_Delt += tensor( data_copy )

  return H_Delt

