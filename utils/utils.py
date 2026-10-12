import networkx as nx
import numpy as np
import libnum

def read_goodcadicaloutput(file):
    lines = []
    with open(file, "r") as f:
        lines = f.readlines()

    j = 0
    sat = False
    totalproctime = -0.1
    totalrealtime = -0.1

    while j<len(lines):
        line = lines[j]
        if "[ result ]" in line:
            j += 2
            line = lines[j]
            if "SATISFIABLE" in line:
                # print("good case")
                sat = True
            else:
                j = len(lines)

        if "[ resources ]" in line:
            j+=2
            line = lines[j]
            totalproctime = float(line.split()[-2])
            j+=1
            line = lines[j]
            totalrealtime = float(line.split()[-2])

        j+=1

    return sat, totalproctime, totalrealtime


def read_cadicaloutput(file):
    lines = []
    with open(file, "r") as f:
        lines = f.readlines()

    j = 0
    unknown = False
    totalproctime = -0.1
    totalrealtime = -0.1

    while j<len(lines):
        line = lines[j]
        if "[ result ]" in line:
            j += 2
            line = lines[j]
            if "UNKNOWN" in line:
                # print("good case")
                unknown = True
            else:
                j = len(lines)

        if "[ resources ]" in line:
            j+=2
            line = lines[j]
            totalproctime = float(line.split()[-2])
            j+=1
            line = lines[j]
            totalrealtime = float(line.split()[-2])

        j+=1

    return unknown, totalproctime, totalrealtime


def create_clauses(cnf):
  '''
    Take a dimacs formatted clause and convert it to a dictionary
  '''

  infos = cnf.split( "\n" )

  clauses = {}

  n_clause = 0
  literals = 0

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
            literals += 1
        n_clause += 1


  return n_vars, n_clauses, clauses, literals

def simplify_SAT(clauses: dict, n_vars: int, n_clauses: int):
    """
    Simplify a SAT formula recursively by unit propagation.
    
    clauses: dict[int, list[int]]
        Example: {0: [1, -3], 1: [2], 2: [-1, 4]}
    n_vars: int
        Number of variables
    n_clauses: int
        Number of clauses (not strictly needed, but kept for compatibility)

    Returns:
        new_vars, new_clauses, new_formula, n_literals
    """

    # Work on a copy so the input is not modified outside
    clauses = {k: list(v) for k, v in clauses.items()}
    removed_variables = set()

    changed = True
    while changed:
        changed = False

        # Find all current unit clauses
        unit_assignments = {}
        unit_clause_keys = []

        for k, v in clauses.items():
            if len(v) == 1:
                lit = v[0]
                var = abs(lit)
                val = (lit > 0)

                # Optional: detect contradiction x and -x both as unit clauses
                if var in unit_assignments and unit_assignments[var] != val:
                    raise ValueError(f"Contradiction detected on variable {var}")

                unit_assignments[var] = val
                unit_clause_keys.append(k)

        if not unit_clause_keys:
            break

        changed = True
        removed_variables.update(unit_assignments.keys())

        new_clauses_dict = {}
        new_idx = 0

        for k, clause in clauses.items():
            # Skip the unit clauses themselves
            if k in unit_clause_keys:
                continue

            satisfied = False
            new_clause = []

            for lit in clause:
                var = abs(lit)

                if var not in unit_assignments:
                    new_clause.append(lit)
                else:
                    assigned_val = unit_assignments[var]

                    # literal is satisfied
                    if (lit > 0 and assigned_val) or (lit < 0 and not assigned_val):
                        satisfied = True
                        break
                    # otherwise literal is false, so we drop it

            if not satisfied:
                # If new_clause becomes empty, formula is unsatisfiable under propagation
                if len(new_clause) == 0:
                    raise ValueError("Empty clause generated: formula is unsatisfiable")
                new_clauses_dict[new_idx] = new_clause
                new_idx += 1

        clauses = new_clauses_dict

    # Build rescaling map for variables that remain
    remaining_vars = sorted(
        {abs(lit) for clause in clauses.values() for lit in clause}
    )

    old_to_new = {old_var: new_var for new_var, old_var in enumerate(remaining_vars, start=1)}

    # Apply rescaling
    rescaled_clauses = {}
    for k, clause in clauses.items():
        new_clause = []
        for lit in clause:
            old_var = abs(lit)
            new_var = old_to_new[old_var]
            new_clause.append(new_var if lit > 0 else -new_var)
        rescaled_clauses[k] = new_clause

    new_vars = len(remaining_vars)
    new_clauses = len(rescaled_clauses)
    n_literals = sum(len(v) for v in rescaled_clauses.values())

    return new_vars, new_clauses, rescaled_clauses, n_literals



# Given bit length, generate corresponding primes
def generateCompositeNum( bitsize ):

    r=libnum.randint_bits(bitsize)

    # print ("Random: %d Length: %d" % (r,libnum.len_in_bits(r)))


    p=libnum.generate_prime(bitsize)

    # print ("\nPrime (p): %d. Length: %d bits, Digits: %d" % (p,libnum.len_in_bits(p), len(str(p)) ))  


    q=libnum.generate_prime(bitsize)
    # print ("\nPrime (q): %d. Length: %d bits, Digits: %d" % (q,libnum.len_in_bits(q), len(str(q)) ))

    N=p*q
    # print ("\nProduct (N): %d. Length: %d bits, Digits: %d" % (N,libnum.len_in_bits(N), len(str(N)) ))

    return N, p, q



def creatematrix( cnf, n, m ):

  M = np.zeros( (n, m) )
  
  for k,v in cnf.items():
    for var in v:
      if var < 0:
        M[abs(var)-1,k] = -1
      else:
        M[var-1,k] = 1

  return M


# Output: NetworkX Graph
def nx_graph_from_3cnf(cnf, n, m):

  M = creatematrix( cnf, n, m )

  # Give names to the nodes in the two node sets
  U = [ "v{}".format(i+1) for i in range(M.shape[0]) ]
  V = [ "c{}".format(i) for i in range(M.shape[1]) ]

  # Create the graph and add each set of nodes
  G = nx.Graph()
  G.add_nodes_from(U, bipartite=0)
  G.add_nodes_from(V, bipartite=1)

  # Find the non-zero indices in the biadjacency matrix to connect 
  # those nodes

  for i in range(n):
    for j in range(m):
      if M[i,j] == 1:
        G.add_edge(U[i], V[j], color="k")
      elif M[i,j] == -1:
        G.add_edge(U[i], V[j], color="r")

  return G




def detect_planarity( G ):

  return nx.is_planar( G )



from shapely.geometry import LineString, Point
from itertools import combinations
import math

def _cardinal_approach_points(crossing_xy, node_positions, delta=0.05):
    cx, cy = crossing_xy

    cardinals = {
        'E': (cx + delta, cy),
        'W': (cx - delta, cy),
        'N': (cx,         cy + delta),
        'S': (cx,         cy - delta),
    }

    cardinal_angles = {'E': 0, 'N': 90, 'W': 180, 'S': 270}

    def angle_to(pos):
        return math.degrees(math.atan2(pos[1] - cy, pos[0] - cx)) % 360

    def angle_diff(a, b):
        return min(abs(a - b), 360 - abs(a - b))

    nodes = list(node_positions.keys())
    node_angles = {n: angle_to(node_positions[n]) for n in nodes}

    available = set(cardinal_angles.keys())
    assignment = {}

    while available and len(assignment) < len(nodes):
        best_node, best_card, best_diff = None, None, float('inf')
        for n in nodes:
            if n in assignment:
                continue
            for c in available:
                diff = angle_diff(node_angles[n], cardinal_angles[c])
                if diff < best_diff:
                    best_diff = diff
                    best_node, best_card = n, c
        assignment[best_node] = cardinals[best_card]
        available.remove(best_card)

    return assignment


def sort_approaches_clockwise_from_west(crossing_xy, approaches):
    cx, cy = crossing_xy

    def sort_key(item):
        _, (px, py) = item
        angle = math.degrees(math.atan2(py - cy, px - cx)) % 360
        rotated = (angle - 180) % 360
        return -rotated % 360

    return dict(sorted(approaches.items(), key=sort_key))


def detect_crossings(G, pos, delta=0.05):
    intersections = []
    edges = list(G.edges())

    for (u1, v1), (u2, v2) in combinations(edges, 2):
        if len({u1, v1, u2, v2}) < 4:
            continue

        line1 = LineString([pos[u1], pos[v1]])
        line2 = LineString([pos[u2], pos[v2]])

        if not line1.intersects(line2):
            continue

        pt = line1.intersection(line2)

        # Skip non-point intersections (collinear/overlapping edges)
        if not isinstance(pt, Point):
            continue

        crossing_xy = (pt.x, pt.y)

        approaches = _cardinal_approach_points(
            crossing_xy,
            {u1: pos[u1], v1: pos[v1], u2: pos[u2], v2: pos[v2]},
            delta
        )

        sorted_approaches = sort_approaches_clockwise_from_west(crossing_xy, approaches)
        intersections.append(((u1, v1), (u2, v2), pt, sorted_approaches))

    onlycrossings = []
    for val in intersections:
        print(val)
        (var1, cl1) = val[0]
        (var2, cl2) = val[1]
        onlycrossings.append(((var1, cl1), (var2, cl2)))

    return intersections, onlycrossings