import ComprehensiveGreedy
import DataStructure as DS
import ExtremalOpt
import GeneralFunctions
import LayoutAlgorithm as Layout
from operator import itemgetter, attrgetter
import os
import PriorityGreedy
import PriorityRegionGreedy
import RegionGreedy
import sys
from time import time

use = '''
  Require:
  -i : input file name (./Data/sample.tsv)
     ex: -i=./Data/sample.tsv
  -a : choose the greedy algorithm. (comprehensive / onebyone / region / extreme)
     ex: -a=region
  Option:
  -o : output result to a directory
     ex: -o=/web/htdocs/storyline/output/
     defautl: ./output/
  -h : Turn OFF heuristic filtering.
'''

ALGORITHMS = ["comprehensive", "onebyone", "priority_region", "region", "extreme"]

'''
#
# Checks if the new interaction session is an extension from the previous
# timestep.
#
def aaatestExtendedInteractionSession(previous_data, interaction_sessions):
  # Clone the new interaction session.
  new_interaction_sessions = interaction_sessions[:]
  previous_interaction_sessions = previous_data['interaction_sessions']
  # For each IS check if it is an extension from the previous IS.
  for new_session in interaction_sessions:
    for previous_session in previous_interaction_sessions:
      if previous_session.end_time == new_session.start_time:
        is_is_subset_of_pis = previous_session.members.issubset(
            new_session.members)
        pis_is_subset_of_is = new_session.members.issubset(
            previous_session.members)
        # If both IS is subset of both, they belong to the same IS.
        if is_is_subset_of_pis and pis_is_subset_of_is:
          previous_session.end_time = new_session.end_time
          new_interaction_sessions.remove(new_session)
  return previous_interaction_sessions, new_interaction_sessions
'''


def testExtendedInteractionSession(previously_loaded_ISs, loaded_ISs, sort_new=True):
  # Initialize response container.
  extended_ISs = []
  new_ISs = []

  # For each IS check if it is an extension from the previous IS.
  for loaded_IS in loaded_ISs:
    _extended = False
    for prev_IS in previously_loaded_ISs:
      #assert prev_IS.end_time == loaded_IS.start_time, "%d %d" % (prev_IS.end_time, loaded_IS.start_time)

      X = prev_IS.members.issubset(loaded_IS.members)
      Y = loaded_IS.members.issubset(prev_IS.members)
      # If both IS is subset of both, they belong to the same IS.
      if X and Y:
        prev_IS.end_time = loaded_IS.end_time
        extended_ISs.append(prev_IS)
        _extended = True
        break
    if not _extended:
      new_ISs.append(loaded_IS)

  # Sort the new interaction sessions based on their number of common lines.
  if sort_new:
    new_ISs_priority_score = {}
    for idx, new_IS in enumerate(new_ISs):
      best_score = 0
      for prev_IS in previously_loaded_ISs:
        common_members = new_IS.members.intersection(prev_IS.members)
        best_score = max(best_score, len(common_members))
      new_ISs_priority_score[new_IS] = (best_score, idx)
    sorted_new_ISs = [k for v, k in sorted(
      ((v, k) for k, v in new_ISs_priority_score.items()), reverse=True)]
    new_ISs = sorted_new_ISs[:]
  return extended_ISs, new_ISs


def loadNewData(line, previously_loaded_ISs, current_time_step):
  # Initialize response container.
  extended_ISs = []
  new_ISs = []

  # Construct the new timestep's interaction session.
  loaded_interaction_sessions, loaded_characters = readStreamData(
      line, current_time_step)
  # Classify the data into extended/new ISs.
  extended_ISs, new_ISs= testExtendedInteractionSession(
      previously_loaded_ISs, loaded_interaction_sessions)
  # Register connections between the InteractionSessions
  registerConnections(new_ISs, previously_loaded_ISs)
  return extended_ISs, new_ISs


#
# Looks up the common members between subsequent ISs and registers the
# connections for each IS.
#
def registerConnections(interaction_sessions, previously_loaded_ISs):
  # Lookup combinations of IS and make connections.
  for interaction_session_i in interaction_sessions:
    for interaction_session_j in previously_loaded_ISs:
      # Only consider subsequent ISs.
      if interaction_session_i.start_time == interaction_session_j.end_time:
        interaction_session_i.proceeding_interaction_sessions.append(
            interaction_session_j)
        interaction_session_j.following_interaction_sessions.append(
            interaction_session_i)
  return


#
# Constructs new ISs from a line of text.
#
def readStreamData(line, time_step):
  # Initialize values.
  interaction_session_count = 0
  interaction_session_ary = []
  default_location = 0
  character_ary = []
  # Split line text.
  fields = line.split("\t")
  #time_step = int(fields[0])
  #for g in fields[1:]:
  for g in fields[0:]:
    # Parse members
    members = g.strip('\n').split(',')
    name =  '[' + g.strip('\n') +']_'+  str(time_step)
    # Create new IS
    new_is = DS.InteractionSession(interaction_session_count, time_step - 1,
        time_step, name, default_location )
    new_is.addMembers(members)
    # Add to character array
    for member in members:
      if member not in character_ary :
        character_ary.append(member)
    # Save to session array
    interaction_session_ary.append(new_is)
    interaction_session_count += 1
  return (interaction_session_ary , character_ary)

'''
#
# Combines the previous data to the new incoming data.
#
def combineData(previous_data , data):
  # If there is no previous data, return only the new data.
  if not previous_data:
    return data
  # Clone previous data.
  new_data = previous_data
  new_data['time_step'] = data['time_step']
  # Add new character
  for member in data['characters']:
    if member not in previous_data['characters']:
      new_data['characters'].append(member)
  # Sort the new ISs based on how many common members they contain from
  # previous time step. This is used to determine the priority of serial greedy
  # method.
  sort_IS = []
  for session in data['interaction_sessions']:
    max_common_members = GeneralFunctions.computePriority(session,
        previous_data['interaction_sessions'])
    obj = (session, max_common_members)
    sort_IS.append(obj)
  sort_IS = sorted(sort_IS, key=itemgetter(1), reverse=True)
  # Append new ISs to the data.t
  for session, common_member_count in sort_IS:
    new_data['interaction_sessions'].append(session)
  return new_data
'''


#
# Output the layout info into a file.
#
def outputLayout(oflnm, layout, data):
  time_steps = data['time_step']
  characters = data['characters']
  ofl = open(oflnm, 'w')
  ofl.write("name")
  for t in range(time_steps):
    ofl.write('\t')
    ofl.write(str(t))
  ofl.write('\n')
  for member in layout:
    member_coords = layout[member]
    ofl.write(member)
    for time_step in range(time_steps):
      ofl.write('\t')
      if time_step in member_coords:
        ofl.write('%d' % member_coords[time_step])
      else:
        ofl.write(' ')
    ofl.write('\n')
  ofl.close()
  return


#
# Main function.
#
def main(argv):
  # Input file name.
  iflnm = ''
  # Algorithm name.
  algorithm = ''
  # Output directory.
  odir = './output/'
  # Use heuristic flag.
  use_heuristic_evaluator = True

  # Parse the input arguments.
  for arg in argv:
    ary = arg.split('=')
    if ary[0] == '-i':
      iflnm = ary[1]
    elif ary[0] == '-o':
      odir = ary[1]
      if not os.path.exists(odir):
        print 'Path <%s> not found. Creating a new directory <%s>' % (odir,
            odir)
        os.makedirs(odir)
    elif ary[0] == '-a':
      algorithm = ary[1]
      if algorithm not in ALGORITHMS:
        print (('Algorithm named <%s> not found. Choose one from : ' % (
            algorithm)), ALGORITHMS)
        return
    elif ary[0] == '-h':
      print 'Using heuristic filtering is OFF.'
      use_heuristic_evaluator = False

  # Set input file name.
  if iflnm == '':
    print 'Error: input file name not specified.'
    print use
    return

  # Set algorithm name.
  if algorithm == '':
    print 'Error: algorithm type not specified.'
    print use
    return

  # Initialize variables. 
  data = None
  sequence = []
  previous_slot_base_layout = None
  previous_slot_segments = None
  previously_loaded_ISs = []
  cummurative_time_ellapase = 0.0;
  final_slot_base_layout = None
  final_layout = None


  # Start reading file.
  print "Start streaming data... <%s>" % (iflnm)
  ifl = open(iflnm)

  # Determine the solver
  layout_solver = None
  if algorithm == "region":
    layout_solver = RegionGreedy.regionGreedyComputeLayout
  elif algorithm == "priority_region":
    layout_solver = PriorityRegionGreedy.priorityRegionGreedyComputeLayout
  elif algorithm == "onebyone":
    layout_solver = PriorityGreedy.priorityGreedyComputeLayout
  elif algorithm == "comprehensive":
    layout_solver = ComprehensiveGreedy.comprehensiveGreedyComputeLayout
  elif algorithm == "extreme":
    layout_solver = ExtremalOpt.extremeOptimizationComputeLayout

  #TODO(ytanahashi): try to modify this from time step 0.
  current_time_step = 1
  data = {'time_step': 0, 'characters': [], 'interaction_sessions': []}
  for line in ifl:
    # Load data.
    print "Generating Time Step %d" % current_time_step
    extended_ISs, new_ISs = loadNewData(line, previously_loaded_ISs, current_time_step)
    # Modify data.
    data['time_step'] += 1
    for new_IS in new_ISs:
      data['interaction_sessions'].append(new_IS)
      members = new_IS.members
      for member in members:
        if member not in data['characters']:
          data['characters'].append(member)

    # Start timer.
    timestep_compute_start_time = time()

    # Start to compute layout
    layout, sequence, slot_base_layout, slot_segments, _time_effect = (
        layout_solver(data, (extended_ISs, new_ISs), sequence, previous_slot_base_layout,
            previous_slot_segments, use_heuristic_evaluator))

    # Stop timer.
    timestep_compute_end_time= time()

    # Get time used for layout computation.
    timestep_compute_time_elapse = (timestep_compute_end_time
        - timestep_compute_start_time)

    # Only add the time if computation theoretically effects computation time.
    if _time_effect:
      cummurative_time_ellapase += timestep_compute_time_elapse;
    print 'Timestep %d : layout computation took %.2f seconds.' % (
        current_time_step, timestep_compute_time_elapse)

    # Cache the new layout for the next timestep reference.
    previously_loaded_ISs = extended_ISs + new_ISs
    previous_slot_base_layout = slot_base_layout
    previous_slot_segments = slot_segments

    final_slot_base_layout = slot_base_layout
    final_layout = layout

    # Output layout.
    oflnm = '%s%d.tsv' % (odir, current_time_step)
    outputLayout(oflnm, layout, data)

    # Update the time step.
    current_time_step += 1
  ifl.close()
  print "Overall layout took %.2f seconds" % (cummurative_time_ellapase)
  print "Evaluating the layout..."
  GeneralFunctions.evaluateLayout(data, final_slot_base_layout, final_layout)
  return


if __name__ == '__main__':
  main(sys.argv[1:])
