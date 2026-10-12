
# importing the library
import os
import pickle

ALL = {}
 
# giving directory name
dirname = f'{os.getcwd()}/generator/graphs'
 
# iterating over all files
for file in os.listdir(dirname):
  if file.endswith(".pkl"):
    if not "instances" in file:
      with open( os.path.join( dirname, file ), "rb" ) as f:
        ALL.update( pickle.load(f) )
      os.remove( os.path.join( dirname, file ) )
  else:
    continue

with open( f"{dirname}/instances_simplified.pkl", "wb" ) as f:
  pickle.dump( ALL, f, protocol=pickle.HIGHEST_PROTOCOL )