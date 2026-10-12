import matplotlib.pyplot as plt
import numpy as np
import networkx as nx
from qutip import basis, mcsolve, mesolve
from utils.utils import get_random_graph, get_interactionH, get_H_omega, get_H_delta
from qutip.solver import Options

# We create a fictional model of Hamiltonian which does not consider the x,y position of spin atoms 
# but 1 if they are connected in the original graph, 0 otherwise


primes, data = get_random_graph( 1, 15 )

# print(primes)
# print(data)


G = data["easyG"]

# nx.draw(G)
# plt.show()

n_qubits = G.number_of_nodes()

print(G.edges())

H_int = get_interactionH( G )

print(H_int)

H_omega = get_H_omega( G )

print( H_omega )

H_delta = get_H_delta( G ) 

print( H_delta )


min_delta = -3
max_delta = 2 * np.pi * 1.5

max_omega = 2 * np.pi * 0.7

def H_omega_coeff(t, args):
  if t < 1:
    return 4.398 * t 
  elif 1 <= t <= 3:
    return max_omega
  elif t>= 3:
    return -4.398*t + 17.592
  
def H_delta_coeff(t, args):
  return 3.106175 * t - 3


t = np.linspace( 0, 4, 1000 )

# plt.plot( t, [H_omega_coeff(t1, None) for t1 in t] )
# plt.show()
# plt.plot( t, [H_delta_coeff(t1, None) for t1 in t] )
# plt.show()

options=Options()
options.__setattr__("nsteps", 100000)
options.__setattr__("store_final_state", True)
# options["store_final_state"]=True
# options["nsteps"]=100000
print(options)

H = [H_int,[H_omega,H_omega_coeff], [H_delta, H_delta_coeff]]

psi0 = basis(2**n_qubits, 0)

print(psi0)

output = mesolve(H, psi0, t, [], [psi0*psi0.dag()], options=options)

# print(output.expectlist)
print(output)
print(output.final_state)
# print(output.expect[0])
# print(output.statesarray[-1])

# fig, ax = plt.subplots()
# ax.plot(t, output.expect[0])
# ax.plot(t, output.expect[1])
# ax.set_xlabel('Time')
# ax.set_ylabel('Expectation values')
# ax.legend(("Sigma-Z", "Sigma-Y"))
# plt.show()