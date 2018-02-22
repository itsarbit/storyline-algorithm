import CommonParameters
from itertools import permutations


def separateExtentedAndNew(data):
  # Initialize response variable.
  extended_interaction_sessions = []
  new_interaction_sessions = []
  current_timestep = data['time_step']
  for IS in data['interaction_sessions']:
    if IS.start_time + 1 == current_timestep:
      new_interaction_sessions.append(IS)
    elif IS.end_time == current_timestep:
      extended_interaction_sessions.append(IS)
  append_seq_length = len(new_interaction_sessions)
  print "Timestep: %d, Total IS: %d, New IS: %d, Extending IS: %d" % (
      current_timestep, len(data['interaction_sessions']), append_seq_length,
      len(extended_interaction_sessions))
  return extended_interaction_sessions, new_interaction_sessions


def generateSequenceCombinations(previous_sequence,
    new_interaction_sessions_length, extended_interaction_sessions,
    previous_slot_base_layout):
  # Initialize the sequence pool.
  seq_pool = []
  # Extract all slot numbers occupied by extending ISs.
  occupied_slot_numbers = []
  if previous_slot_base_layout:
    sessions_layout = previous_slot_base_layout.sessions_layout
    for IS in extended_interaction_sessions:
      slot_number = sessions_layout[IS].slot
      occupied_slot_numbers.append(slot_number)
  print 'Occupied slot numbers : ', occupied_slot_numbers
  # Get all open slot numbers.
  open_slot_numbers = []
  for slot_number in range(CommonParameters.SLOTS):
    if slot_number not in occupied_slot_numbers:
      open_slot_numbers.append(slot_number)
  # Generate all combination of sequences
  all_slot_permutations = permutations(open_slot_numbers,
      new_interaction_sessions_length)
  for extending_slots in all_slot_permutations:
    new_seq = previous_sequence + list(extending_slots)
    seq_pool.append(new_seq)
  return seq_pool


def computePriority(session, previous_sessions):
  max_score = -1
  for old_session in previous_sessions:
    if old_session.end_time == session.start_time:
      session_members = session.members
      old_members = old_session.members
      common_members = session_members.intersection(old_members)
      common_member_count = len(common_members)
      if common_member_count > 0:
        #score = len(session.members)
        score = common_member_count
        max_score = max(max_score, score)
  return max_score



def findOccupiedSlots(previous_slot_base_layout, current_timestep):
  previous_occupied_slot_numbers = []
  extended_occupied_slot_numbers = []
  if previous_slot_base_layout:
    sessions_layout = previous_slot_base_layout.sessions_layout
    for IS in sessions_layout:
      slot_number = sessions_layout[IS].slot
      if IS.end_time == current_timestep :
        extended_occupied_slot_numbers.append(slot_number)
      if IS.end_time >= current_timestep - 1 :
        previous_occupied_slot_numbers.append(slot_number)
  return previous_occupied_slot_numbers, extended_occupied_slot_numbers



def generateDynamicSequenceCombinations(previous_seq, previous_occupied_slots,
    extended_occupied_slots, append_seq_length):
  # Generate candidate regions
  candidate_slots = []
  previous_occupied_slots.sort()
  # Generate appended ones
  for slot in previous_occupied_slots:
    # If slot is extended, ignore it since they are already occupied.
    if slot not in extended_occupied_slots:
      candidate_slots.append((slot, 0))
  # Generate above top ones:
  top_slot = previous_occupied_slots[0]
  for i in range(append_seq_length):
    candidate_slots.append((top_slot, -(i + 1)))
  # Generate between ones:
  for slot in previous_occupied_slots:
    for i in range(append_seq_length):
      candidate_slots.append((slot, i + 1))
  # Permutation of all candidate slots.
  all_tuple_permutations = permutations(candidate_slots, append_seq_length)
  slot_tuple_combinations_pool = [list(seq)  for seq in all_tuple_permutations]

  # Create a hash table to avoid redundant slot-based layout.
  hash_table = dict()

  seq_pool = []
  for tuple_combination in slot_tuple_combinations_pool :
    updated_slot_sequence, append_seq = adjustSlots(previous_seq,
        previous_occupied_slots, tuple_combination, append_seq_length)
    new_sequence = updated_slot_sequence + append_seq
    if str(new_sequence) not in hash_table:
      seq_pool.append(new_sequence)
      hash_table[str(new_sequence)] = True
  return seq_pool



#
# Adjust the string-based slot combinations.
#
def adjustSlots(previous_seq, previous_occupied_slot_ids, regions,
    append_seq_length):
  # Initialize variables.
  updated_previous_seq = []
  append_slot_layout = []
  # Consider remapping of previous occupied slots.
  remap_previous_occupied_slot_ids = {}
  previous_occupied_slot_ids.sort()
  last_offset = 0
  for slot_id in previous_occupied_slot_ids:
    minimum_new_slot_id = append_seq_length
    if len(remap_previous_occupied_slot_ids) > 0:
      remapped_max_slot_id = max(remap_previous_occupied_slot_ids.values())
      minimum_new_slot_id = remapped_max_slot_id + (append_seq_length + 1)
    new_slot_id = max(minimum_new_slot_id, slot_id + last_offset)
    if slot_id not in remap_previous_occupied_slot_ids:
      remap_previous_occupied_slot_ids[slot_id] = new_slot_id
      last_offset = new_slot_id - slot_id
  #print 'Appending %d, Map :' % append_seq_length, remap_previous_occupied_slot_ids
  # Map slot id to new ids.
  clone_previous_seq = previous_seq[:]
  clone_previous_seq.sort()
  remap_slot_id = {}
  cummurative_offset = 0
  for slot_id in clone_previous_seq:
    new_slot_id = slot_id + cummurative_offset
    if slot_id in remap_previous_occupied_slot_ids:
      new_slot_id = remap_previous_occupied_slot_ids[slot_id]
      cummurative_offset = new_slot_id - slot_id
    remap_slot_id[slot_id] = new_slot_id
  # Update the previous slot ids.
  for previous_slot_id in previous_seq:
    updated_slot_id = remap_slot_id[previous_slot_id]
    updated_previous_seq.append(updated_slot_id)
  # Parse seq, compute the new slot number
  for tuple_code in regions:
    main_slot_id, offset = tuple_code
    remapped_main_slot_id = remap_previous_occupied_slot_ids[main_slot_id]
    new_slot_number = remapped_main_slot_id + offset
    append_slot_layout.append(new_slot_number)

  # Get a sorted order of slot numbers.
  sorted_combined_sequence = updated_previous_seq + append_slot_layout
  sorted_combined_sequence.sort()
  # Generate a map for compressing slot numbers in the new_slots.
  slot_id_number_map = {}
  for slot_id in sorted_combined_sequence:
    if slot_id not in slot_id_number_map:
      slot_id_number_map[slot_id] = len(slot_id_number_map)
  # Generate re-mapped updated_previous_seq.
  remapped_updated_previous_seq = []
  for slot_id in updated_previous_seq:
    slot_number = slot_id_number_map[slot_id]
    remapped_updated_previous_seq.append(slot_number)
  # Generate re-mapped new_slots.
  remapped_append_slot_layout = []
  for slot_id in append_slot_layout:
    slot_number = slot_id_number_map[slot_id]
    remapped_append_slot_layout.append(slot_number)
  #print 'p', previous_seq
  #print 'u', updated_previous_seq, append_slot_layout
  #print 'r', remapped_updated_previous_seq, remapped_append_slot_layout

  #return updated_previous_seq, remapped_append_slot_layout
  return remapped_updated_previous_seq, remapped_append_slot_layout
