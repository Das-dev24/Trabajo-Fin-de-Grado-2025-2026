import os

os.environ['MPLBACKEND'] = 'QtAgg'

os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
os.environ.setdefault('OMP_NUM_THREADS', '4')
