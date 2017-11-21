from os import mkdir
import hdf5_to_tiff
from multiprocessing import Pool,cpu_count



desired_runs = (
  (  39,  41),
#  (  43,  45),
#  (  58,  60),
#  (  61,  64),
#  (  65,  69),
#  (  70,  70),
#  (  71,  76),
#  (  77,  78),
#  (  79,  85),
#  (  86,  91),

#  (  163, 169),
#  (  170, 173),
#  (  174, 178),
#  (  179, 185),
#  (  187, 188),
#  (  189, 192),
#  (  193, 205),
)

def dump_run_range(x):
  i,j = x
  target_dir = "r{}-{}".format(i,j)
  try:
    os.mkdir(target_dir)
  #TODO: better error handling
  except:
    "target dir ({}) probably already exists -- not making.".format(target_dir)

  try:
    hdf5_to_tiff.get_brightest(range(i,j+1), target_dir)
  #TODO: better error handling
  except:
    "Shrug... something bad happened with TJ's code. Blame TJ. I was working on {}".format(target_dir)

nprocs = cpu_count()
print "Running on {} cores".format(nprocs)
p = Pool(nprocs)
p.map(dump_run_range, desired_runs)
