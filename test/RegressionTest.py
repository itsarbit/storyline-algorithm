import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import StreamStoryline

INPUT_FILE = ["starwars", "thematrix"]

#ALGORITHMS = ["comprehensive" ]
#ALGORITHMS = ["extreme", "region", "priority_region"]
ALGORITHMS = ["priority_region"]


RUN_TIMES = 1

# run each algorithm several times and logged to folders
for file_name in INPUT_FILE:
    file_fullpath = "../data/" + file_name + "_list.txt"
    for algo in ALGORITHMS:
        for i in range(RUN_TIMES):
            args = []
            args.append("-i=" + file_fullpath)
            args.append("-a=" + algo)
            args.append("-o=../output/")
            # args.append("-h")
            StreamStoryline.main(args)
