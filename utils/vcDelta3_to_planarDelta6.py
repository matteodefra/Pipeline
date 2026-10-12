''' 

		Implement the reduction from Node Cover (Verrtex Cover) with bounded degree 3 and allowed crossings
		to Planar Vertex Cover with bounded degree 6. The reduction is based on replacing each crossover in 
		the planar representation of G with a subgraph H eliminating the corresponding crossings

'''
import networkx as nx
from typing import Tuple
import utils

def try_planarity(G: nx.Graph):
	return nx.check_planarity( G, True )



def create_subgraph( crossing, index ):
	'''
		Given a crossing, replace it with a subgraph
	'''
	H = nx.Graph()
	index = str(index)
	# involved = 

	couple1, couple2 = crossing[0], crossing[1]

	centralpoint = crossing[2]
	coords = crossing[3]

	coordslist = list(coords.items())

	print(coordslist)

	leftmostx = centralpoint.x - coordslist[0][1][0] # ()
	upmosty = centralpoint.y - coordslist[1][1][1] # ()

	portionx = abs(centralpoint.x - leftmostx)/5
	portiony = abs(upmosty - centralpoint.y)/3

	namevertexE = coordslist[0][0]
	namevertexN = coordslist[1][0]
	namevertexW = coordslist[2][0]
	namevertexS = coordslist[3][0]

	gadgetname = namevertexE+"_"+namevertexN+"_"+namevertexW+"_"+namevertexS

	print(gadgetname)

	H.add_node( "{}_a".format(namevertexE+index), pos=coordslist[0][1] )
	H.add_node( "{}_a".format(namevertexN+index), pos=coordslist[1][1] )
	H.add_node( "{}_a".format(namevertexW+index), pos=coordslist[2][1] )
	H.add_node( "{}_a".format(namevertexS+index), pos=coordslist[3][1] )

	H.add_node( "{}_g1".format(gadgetname), pos=(coordslist[0][1][0]+portionx, coordslist[0][1][1]+2*portiony) )
	H.add_node( "{}_g2".format(gadgetname), pos=(coordslist[0][1][0]+portionx, coordslist[0][1][1]+portiony) )
	H.add_node( "{}_g3".format(gadgetname), pos=(coordslist[0][1][0]+portionx, coordslist[0][1][1]-portiony) )
	H.add_node( "{}_g4".format(gadgetname), pos=(coordslist[0][1][0]+portionx, coordslist[0][1][1]-2*portiony) )

	H.add_node( "{}_g5".format(gadgetname), pos=(coordslist[0][1][0]+2*portionx, coordslist[0][1][1]+2*portiony) )
	H.add_node( "{}_g6".format(gadgetname), pos=(coordslist[0][1][0]+2*portionx, coordslist[0][1][1]-2*portiony) )

	H.add_node( "{}_g7".format(gadgetname), pos=(coordslist[0][1][0]+3*portionx, coordslist[0][1][1]) )

	H.add_node( "{}_g8".format(gadgetname), pos=(coordslist[0][1][0]+4*portionx, coordslist[0][1][1]+1*portiony) )
	H.add_node( "{}_g9".format(gadgetname), pos=(coordslist[0][1][0]+4*portionx, coordslist[0][1][1]-1*portiony) )



	H.add_node( "{}_g10".format(gadgetname), pos=(coordslist[2][1][0]-portionx, coordslist[2][1][1]+2*portiony) )
	H.add_node( "{}_g11".format(gadgetname), pos=(coordslist[2][1][0]-portionx, coordslist[2][1][1]+portiony) )
	H.add_node( "{}_g12".format(gadgetname), pos=(coordslist[2][1][0]-portionx, coordslist[2][1][1]-portiony) )
	H.add_node( "{}_g13".format(gadgetname), pos=(coordslist[2][1][0]-portionx, coordslist[2][1][1]-2*portiony) )

	H.add_node( "{}_g14".format(gadgetname), pos=(coordslist[2][1][0]-2*portionx, coordslist[2][1][1]+2*portiony) )
	H.add_node( "{}_g15".format(gadgetname), pos=(coordslist[2][1][0]-2*portionx, coordslist[2][1][1]-2*portiony) )

	H.add_node( "{}_g16".format(gadgetname), pos=(coordslist[2][1][0]-3*portionx, coordslist[2][1][1]) )

	H.add_node( "{}_g17".format(gadgetname), pos=(coordslist[2][1][0]-4*portionx, coordslist[2][1][1]+1*portiony) )
	H.add_node( "{}_g18".format(gadgetname), pos=(coordslist[2][1][0]-4*portionx, coordslist[2][1][1]-1*portiony) )

	H.add_edges_from( [ 
		( "{}_a".format(namevertexE+index), "{}_g1".format(gadgetname) ), 
		( "{}_a".format(namevertexE+index), "{}_g4".format(gadgetname) ),
		( "{}_g1".format(gadgetname), "{}_g2".format(gadgetname) ),
		( "{}_g2".format(gadgetname), "{}_g3".format(gadgetname) ),
		( "{}_g3".format(gadgetname), "{}_g4".format(gadgetname) ),
		( "{}_g1".format(gadgetname), "{}_g5".format(gadgetname) ),
		( "{}_g2".format(gadgetname), "{}_g5".format(gadgetname) ),
		( "{}_g3".format(gadgetname), "{}_g6".format(gadgetname) ),
		( "{}_g4".format(gadgetname), "{}_g6".format(gadgetname) ),
		( "{}_g5".format(gadgetname), "{}_g6".format(gadgetname) ),
		( "{}_g5".format(gadgetname), "{}_g8".format(gadgetname) ),
		( "{}_g6".format(gadgetname), "{}_g9".format(gadgetname) ),
		( "{}_g7".format(gadgetname), "{}_g8".format(gadgetname) ),
		( "{}_g7".format(gadgetname), "{}_g9".format(gadgetname) ),
	] )


	H.add_edges_from( [ 
		( "{}_a".format(namevertexN+index), "{}_g1".format(gadgetname) ), 
		( "{}_a".format(namevertexN+index), "{}_g5".format(gadgetname) ), 
		( "{}_a".format(namevertexN+index), "{}_g10".format(gadgetname) ), 
		( "{}_a".format(namevertexN+index), "{}_g14".format(gadgetname) ),
	] )

	H.add_edges_from( [ 
		( "{}_a".format(namevertexS+index), "{}_g4".format(gadgetname) ), 
		( "{}_a".format(namevertexS+index), "{}_g6".format(gadgetname) ), 
		( "{}_a".format(namevertexS+index), "{}_g13".format(gadgetname) ), 
		( "{}_a".format(namevertexS+index), "{}_g15".format(gadgetname) ),
	] )

	H.add_edges_from( [ 
		( "{}_a".format(namevertexW+index), "{}_g10".format(gadgetname) ), 
		( "{}_a".format(namevertexW+index), "{}_g13".format(gadgetname) ),
		( "{}_g10".format(gadgetname), "{}_g11".format(gadgetname) ),
		( "{}_g11".format(gadgetname), "{}_g12".format(gadgetname) ),
		( "{}_g12".format(gadgetname), "{}_g13".format(gadgetname) ),
		( "{}_g10".format(gadgetname), "{}_g14".format(gadgetname) ),
		( "{}_g11".format(gadgetname), "{}_g14".format(gadgetname) ),
		( "{}_g12".format(gadgetname), "{}_g15".format(gadgetname) ),
		( "{}_g13".format(gadgetname), "{}_g15".format(gadgetname) ),
		( "{}_g14".format(gadgetname), "{}_g15".format(gadgetname) ),
		( "{}_g14".format(gadgetname), "{}_g17".format(gadgetname) ),
		( "{}_g15".format(gadgetname), "{}_g18".format(gadgetname) ),
		( "{}_g16".format(gadgetname), "{}_g17".format(gadgetname) ),
		( "{}_g16".format(gadgetname), "{}_g18".format(gadgetname) ),
	] )

	H.add_edges_from( [
		( "{}_g5".format(gadgetname), "{}_g14".format(gadgetname) ),
		( "{}_g6".format(gadgetname), "{}_g15".format(gadgetname) ),
		( "{}_g8".format(gadgetname), "{}_g17".format(gadgetname) ),
		( "{}_g9".format(gadgetname), "{}_g18".format(gadgetname) ),
	] )

	return H