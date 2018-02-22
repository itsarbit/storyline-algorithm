from itertools import combinations
import LayoutAlgorithm as Layout
import GeneralFunctions


#
# A class object which determines a combination of IS and its state.
#
class ISCombo:

  def __init__(self, is_list, evals):
    interaction_sessions = [interaction_session for interaction_session in is_list]
    self.sorted_is_list = sorted(interaction_sessions, key=lambda IS: IS.start_time)

    score = {'deviation': 0, 'crossovers': 0, 'white_space': 0}
    for interaction_session in is_list:
      is_score = evals[interaction_session]
      for key, val in is_score.items():
        score[key] += val
    self.score = score

  def __str__(self):
    name_list = [tmp_is.name for tmp_is in self.sorted_is_list]
    return str(name_list)

  def __repr__(self):
    return self.__str__()


#
# Start loading the data and 
#
def extremeOptimizationComputeLayout(data, classified_ISs, previous_sequence,
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
    (best_layout, best_fitness, best_seq, best_slot_base_layout,
        best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
        fitness_cache, previous_slot_base_layout, previous_slot_segments)
    # If there are no new ISs, there is actually no need to re-conduct layout computation.
    affects_computation_time = False
  else:
    # Now we need to decide the slot number of each new appended IS.
    if len(previous_sequence) == 0:
      # just simply assign a slot number in ASC order
      seq_pool = []
      seq = []
      for i in range(append_seq_length):
        seq.append(i)
      seq_pool.append(seq)
      # Evaluate
      (best_layout, best_fitness, best_seq, best_slot_base_layout,
          best_slot_segments) = Layout.evaluateSequences(seq_pool, data,
          fitness_cache, None, None)
    else:
      for i in range(append_seq_length):
        # Generate sequence pool for new ISs one by one.
        previous_occupied_slots, extended_occupied_slots = (
            GeneralFunctions.findOccupiedSlots(previous_slot_base_layout,
            current_timestep))
        seq_pool = GeneralFunctions.generateDynamicSequenceCombinations(
            previous_sequence, previous_occupied_slots,
            extended_occupied_slots, 1)

        # Evaluate
        #s_t = time()
        if not use_heuristic_evaluator:
          (best_layout, best_fitness,best_seq, best_slot_base_layout,
               best_slot_segments) = Layout.evaluateSequences(
               seq_pool, data, fitness_cache, None, None)
        else:
          modified_interaction_sessions = [data['interaction_sessions'][len(seq_pool[0]) - 1]]
          (best_layout, best_fitness, best_seq, best_slot_base_layout,
                best_slot_segments) = Layout.evaluateSequencesUsingHeuristics(
                seq_pool, data, fitness_cache, previous_slot_base_layout, previous_slot_segments, modified_interaction_sessions)
        #e_t = time()
        #print 'Evaluating seq_pool took %.2f seconds' % (e_t - s_t)
 
        # Update previous status
        previous_slot_base_layout = best_slot_base_layout
        previous_slot_segments = best_slot_segments
        previous_sequence = best_seq


  ###################################################################
  ############  UNTIL HERE IS SERIAL-DYNAMIC LAYOUT  ################
  ###################################################################
  # Start EXTREMAL-OPTIMIZATION process.
  if append_seq_length > 0 :
    # Get current slot counts.
    slot_count = len(best_slot_base_layout.slots)
    # Get detailed evaluation on each interaction session.
    detail_evals = {}
    Layout.evaluateLayout(best_layout, best_slot_base_layout,
        data['time_step'], detail_evals)
    print 'Detail Evaluations: ', detail_evals
    #print 'SlotBaseLayout', best_slot_base_layout.slots
    # Generate ISCombos.
    combo_collection = []
    # Extract all slot segments.
    list_of_slot_segments = []
    for slotsegments_in_a_slot in best_slot_segments.slot_segments.values():
      list_of_slot_segments.extend(slotsegments_in_a_slot)
    # Extract combinations of ISs in each slot segments.
    for slot_segment in list_of_slot_segments:
      interaction_sessions = slot_segment.interaction_sessions
      sorted_interaction_sessions = sorted(interaction_sessions,
          key=lambda interaction_session: interaction_session.start_time)
      is_count = len(interaction_sessions)
      for i in range(1, is_count + 1):
        list_of_subsequent_combos = []
        for head_idx in range(0, is_count + 1 - i):
          subsequent_combo = sorted_interaction_sessions[head_idx:head_idx + i]
          list_of_subsequent_combos.append(subsequent_combo)
        for combo in list_of_subsequent_combos:
          is_combo = ISCombo(list(combo), detail_evals)
          combo_collection.append(is_combo)
    # Sort the ISCombos based on their score.
    worst_deviation_combos = sorted(combo_collection,
      key=lambda is_combo: is_combo.score['deviation'], reverse=True)

    hashed_potential_sequences = [hash(str(best_seq))] 
    # Improve the layout.
    _iterate = True
    while _iterate:
      _iterate = False
      best_seq_clone = [seq_val * 2 + 1 for seq_val in best_seq]
      # Attempt to improve the layout from the worst ISCombo.
      for is_combo in worst_deviation_combos:
        potential_seq_pool = []
        for potential_slot_idx in range(slot_count * 2 + 1):
          potential_sequence = []
          for IS_idx, IS in enumerate(data['interaction_sessions']):
            if IS in is_combo.sorted_is_list:
              potential_sequence.append(potential_slot_idx)
            else:
              potential_sequence.append(best_seq_clone[IS_idx])
          _validity = Layout.decodeSequence(potential_sequence, data['interaction_sessions'])
          if _validity:
            # Reorganize potential_sequence.
            mod_list = dict(zip(potential_sequence, potential_sequence)).keys()
            mod_list.sort()
            slot_id_number_map = {}
            for number, slot_id in enumerate(mod_list):
              slot_id_number_map[slot_id] = number
            remapped_potential_sequence = []
            for slot_id in potential_sequence:
              remapped_potential_sequence.append(slot_id_number_map[slot_id])
            # Append the new potential sequence to the pool.
            hash_val = hash(str(remapped_potential_sequence))
            if hash_val not in hashed_potential_sequences:
              hashed_potential_sequences.append(hash_val)
              potential_seq_pool.append(remapped_potential_sequence)
          else:
            # This shift is impossible due to preoccupied slot.
            pass
        # Add the current one in case there is no improvement.
        potential_seq_pool.append(best_seq)

        print "\n MOVING!", is_combo, is_combo.score
        for IS in is_combo.sorted_is_list:
          print IS.toString(), detail_evals[IS]
        print 'ORIGINAL SEQ', best_seq
        if len(potential_seq_pool) > 0:
          #(potential_best_layout, potential_best_fitness, potential_best_seq,
          #    potential_best_slot_base_layout, potential_best_slot_segments) = (
          #    Layout.evaluateSequences(potential_seq_pool, data, fitness_cache,
          #    None, None))
          modified_interaction_sessions = is_combo.sorted_is_list[:]
          (potential_best_layout, potential_best_fitness, potential_best_seq,
              potential_best_slot_base_layout, potential_best_slot_segments) = (
              Layout.evaluateSequencesUsingHeuristicsMiddleModified(potential_seq_pool,
                data, fitness_cache, None, None, modified_interaction_sessions, is_combo.score, new=False))
          if potential_best_fitness and potential_best_fitness < best_fitness:
            print "IMPROVED!", best_fitness, '-->', potential_best_fitness
            print "\t BY MOVING!", is_combo
            best_layout = potential_best_layout
            best_fitness = potential_best_fitness
            best_seq = potential_best_seq
            best_slot_base_layout = potential_best_slot_base_layout
            best_slot_segments = potential_best_slot_segments
            _iterate = True
            
            previous_slot_base_layout = best_slot_base_layout
            previous_slot_segments = best_slot_segments
            previous_sequence = best_seq
        
            break
          else:
            print 'NO IMPROVMENT ...'
        else:
          print 'NO POSSIBLE MOVE...'

    Layout.printOutSlotSegments(best_slot_segments)
            

  print "best fitness: %d" % (best_fitness)
  return best_layout, best_seq, best_slot_base_layout, best_slot_segments, affects_computation_time
