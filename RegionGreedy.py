import GeneralFunctions
import LayoutAlgorithm as Layout


#
# Starting computing layout.
#
def regionGreedyComputeLayout(data, classified_ISs, previous_sequence,
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

  # Consttruct the potential slot distributions.
  if append_seq_length == 0 :
    seq_pool = [previous_sequence]
    (best_layout, best_fitness,best_seq, best_slot_base_layout,
        best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
        fitness_cache, previous_slot_base_layout, previous_slot_segments)
    affects_computation_time = False
  else:
    # Now we need to decide the slot number of each new appended IS.
    if len(previous_sequence) == 0:
      # Just simply assign a slot number in ASC order
      seq_pool = []
      seq = []
      for i in range(append_seq_length):
        seq.append(i)
      seq_pool.append(seq)
      # Evaluate
      (best_layout, best_fitness,best_seq, best_slot_base_layout,
          best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
          fitness_cache, None, None)
    else :
      # Generate a sequence pool which contains all combinations of sequence.
      previous_occupied_slots, extended_occupied_slots = (
          GeneralFunctions.findOccupiedSlots(previous_slot_base_layout,
          current_timestep))
      seq_pool = GeneralFunctions.generateDynamicSequenceCombinations(
          previous_sequence, previous_occupied_slots, extended_occupied_slots,
          append_seq_length)
      print "seq_pool size: %d" % len(seq_pool)
      if not use_heuristic_evaluator:
          (best_layout, best_fitness,best_seq, best_slot_base_layout,
              best_slot_segments) = Layout.evaluateSequences(
              seq_pool, data, fitness_cache, None, None)
      else:
        modified_interaction_sessions = data['interaction_sessions'][-append_seq_length:]
        (best_layout, best_fitness, best_seq, best_slot_base_layout,
            best_slot_segments) = Layout.evaluateSequencesUsingHeuristics(
            seq_pool, data, fitness_cache, previous_slot_base_layout, previous_slot_segments, modified_interaction_sessions)

  print "best sequence: %s, best fitness: %d" % (best_seq, best_fitness)
  return best_layout, best_seq, best_slot_base_layout, best_slot_segments, affects_computation_time
