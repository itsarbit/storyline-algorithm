storyline_python
================

##  Installation

pip install cvxopt


## Input format

Each line represents one time step, groups are separated by TAB, members in the same group are concatenated by COMMA

Example: 

A,B,C	D,E

A,B	C,D,E


## How to run the algorithm

python StreamStoryline.py -i=./your_data.tsv -a=choose_a_algorithm -o=./output

Require:
-i : input file name (./data/sample.tsv)
	ex: -i=./Data/sample.tsv
	
-a : choose the greedy algorithm. (comprehensive / onebyone / region / extreme)
	ex: -a=region
	
Optional:
-o : output result to a directory
	ex: -o=/web/htdocs/storyline/output/
	defautl: ./output/
	
-h : Turn OFF heuristic filtering.
