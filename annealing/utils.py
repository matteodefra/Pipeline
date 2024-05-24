import pickle
import networkx as nx



def embed( G ):
  # Embed the nonUD graph instance in a 3D array
  return


def getGraphs():
  # We get the graph instances which are possibly suitable for a 3d version
  # Max degree \Delta <= 6
  with open( "filtered_instances.pkl", "rb" ) as f:
    dic = pickle.load( f )

  return dic