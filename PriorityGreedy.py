import GeneralFunctions
import LayoutAlgorithm as Layout


#
# Start layout computation.
#
def priorityGreedyComputeLayout(data, classified_ISs, previous_sequence,
    previous_slot_base_layout, previous_slot_segments, use_heuristic_evaluator):
  # Initialize response variables.
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  affects_computation_time = True

  # Initialize variables.
  fitness_cache = dict()
  current_timestep = data['time_step']
  extended_interaction_sessions, new_interaction_sessions = classified_ISs
  append_seq_length = len(new_interaction_sessions)

  # If there are no new ISs, the genome sequence is the same to previous.
  if append_seq_length == 0 :
    seq_pool = [previous_sequence]
    (best_layout, best_fitness, best_seq, best_slot_base_layout,
        best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
        fitness_cache, previous_slot_base_layout, previous_slot_segments)
    # If there are no new ISs, there is actually no need to re-conduct layout computation.
    affects_computation_time = False
  else:
    # For each new IS, test where its best to append.
    for i in range(append_seq_length):
      seq_pool = GeneralFunctions.generateSequenceCombinations(previous_sequence,
          1, extended_interaction_sessions, previous_slot_base_layout)
      if not use_heuristic_evaluator:
          (best_layout, best_fitness, best_seq, best_slot_base_layout,
              best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
              fitness_cache, previous_slot_base_layout, previous_slot_segments)
      else:
          modified_interaction_sessions = [data['interaction_sessions'][len(seq_pool[0]) - 1]]
          (best_layout, best_fitness, best_seq, best_slot_base_layout,
                best_slot_segments) = Layout.evaluateSequencesUsingHeuristics(
                seq_pool, data, fitness_cache, previous_slot_base_layout, previous_slot_segments, modified_interaction_sessions)
      # Update the previous layout info.
      previous_sequence = best_seq
      previous_slot_base_layout = best_slot_base_layout
      previous_slot_segments = best_slot_segments
      # Add the assigned IS to the extended ISs.
      extended_interaction_sessions.append(
          data['interaction_sessions'][len(previous_sequence) - 1])

  print "best sequence: %s, best fitness: %d" % (best_seq, best_fitness)
  return best_layout, best_seq, best_slot_base_layout, best_slot_segments, affects_computation_time
