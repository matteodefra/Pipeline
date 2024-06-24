import pickle
import os
import networkx as nx


def convert_graph( p: int, q: int, G: nx.Graph ):

  lines = []

  nodes = list(G.nodes())
  edges = list(G.edges())

  footer = f"{len(nodes)} {len(edges)}"

  # f = open(f'graphs/graphformat/{p}_{q}.graph', 'w')
  # f.write(f"{footer}\n")
  lines.append( f"{footer}\n" )

  for node in nodes:
    line = ""
    for e in edges:

      if e[0] == e[1]:
        pass
      else:
        if e[0] == node:
          line += f"{e[1]+1} "
        elif e[1] == node:
          line += f"{e[0]+1} "

    line = line.strip()
    # f.write(f"{line}\n")
    lines.append( f"{line}\n" )

  # f.close()
  return lines


def convert_graphs():

  with open( os.path.abspath( "graphs/fullinstances.pkl" ), "rb" ) as f:
    dic = pickle.load(f)

  # print(dic[(17, 19)]["Easy_G"].edges())
  # for e in list(dic[(17, 19)]["Easy_G"].edges()):
  #   if e[0] == e[1]:
  #     print("Ops")
  #     print(e)

  # print(dic[(17, 19)]["SAT"])

  for k,v in dic.items():
    print(f"Graph {k}")

    G : nx.Graph = v["easyG"]

    nodes = list(G.nodes())
    edges = list(G.edges())

    footer = f"{len(nodes)} {len(edges)}"

    f = open(f'graphs/graphformat/{k[0]}_{k[1]}.graph', 'w')
    f.write(f"{footer}\n")

    for node in nodes:
      line = ""
      for e in edges:

        if e[0] == e[1]:
          pass
        else:
          if e[0] == node:
            line += f"{e[1]+1} "
          elif e[1] == node:
            line += f"{e[0]+1} "

      line = line.strip()
      f.write(f"{line}\n")

    f.close()


if __name__ == "__main__":
  convert_graphs()