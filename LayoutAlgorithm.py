from cvxopt import matrix
from cvxopt import solvers
import numpy
from sets import Set
from time import time

import CommonParameters
import DataStructure as DS
import LayoutFromScratchAlgorithm

FITTNESS_WEIGHT = {'deviation':5, 'crossover':5, 'whitespace':1}
solvers.options['show_progress'] = False


def classifyProceedingLineSegments(slot_base_layout,
    added_interaction_sessions):
  # Classify only the lines in the NEW interaction sessions.
  for interaction_session in added_interaction_sessions:
    if interaction_session in slot_base_layout.sessions_layout:
      session_layout = slot_base_layout.sessions_layout[interaction_session]
      proceeding_interaction_sessions = (
          interaction_session.proceeding_interaction_sessions)

      for proceeding_interaction_session in proceeding_interaction_sessions:
        proceeding_session_layout = (
            slot_base_layout.sessions_layout[proceeding_interaction_session])
        intersecting_members = interaction_session.members.intersection(
            proceeding_interaction_session.members)
        if proceeding_session_layout.slot < session_layout.slot:
          for intersecting_member in intersecting_members:
            session_layout.rising_lines.add(intersecting_member)
        elif proceeding_session_layout.slot == session_layout.slot:
          for intersecting_member in intersecting_members:
            session_layout.static_lines.add(intersecting_member)
        elif proceeding_session_layout.slot > session_layout.slot:
          for intersecting_member in intersecting_members:
            session_layout.dropping_lines.add(intersecting_member)
  return


#TODO(ytanahashi): implement also will drop etc.
def classifyEmergingLineSegments(slot_base_layout, added_interaction_sessions):
  for interaction_session in added_interaction_sessions:
    if interaction_session in slot_base_layout.sessions_layout:
      session_layout = slot_base_layout.sessions_layout[interaction_session]
      classified_members = Set(session_layout.getClassifiedMembers())
      full_members = interaction_session.members
      nonclassified_members = full_members.difference(classified_members)
      for member in nonclassified_members:
        session_layout.emerging_lines['will_rise'].add(member)
  return


def checkAllLinsegmentsAreClassified(slot_base_layout):
  for interaction_session in slot_base_layout.sessions_layout:
    session_layout = slot_base_layout.sessions_layout[interaction_session]
    classified_members = session_layout.getClassifiedMembers()
    full_members = interaction_session.members
    if len(classified_members) != len(full_members):
      return False
  return True


def classifyLineSegments(slot_base_layout, added_interaction_sessions):
  classifyProceedingLineSegments(slot_base_layout, added_interaction_sessions)
  classifyEmergingLineSegments(slot_base_layout, added_interaction_sessions)
  return


def getCommonInteractionSession(sessions_1, sessions_2):
  common_sessions = []
  for session_1 in sessions_1:
    for session_2 in sessions_2:
      if session_1 == session_2:
        common_sessions.append(session_1)
  return common_sessions


def getForerunningInteractionSessions(subject_interaction_session,
    interaction_sessions, is_sorted=False):
  sorted_interaction_sessions = []
  if is_sorted == False:
    sorted_interaction_sessions = sorted(interaction_sessions,
        key=lambda interaction_session: interaction_session.start_time)
  else:
    sorted_interaction_sessions = interaction_sessions[:]

  subject_is_idx = sorted_interaction_sessions.index(
      subject_interaction_session)
  tmp_forerunning_interaction_sessions = (
      sorted_interaction_sessions[:subject_is_idx])
  forerunning_interaction_sessions = []
  for tmp_is in tmp_forerunning_interaction_sessions:
    if tmp_is.end_time == subject_interaction_session.start_time:
      forerunning_interaction_sessions.append(tmp_is)
  return forerunning_interaction_sessions


def assignMemberAlignment(slot_base_layout, added_interaction_sessions):
  # This function assigns the layout for the line segments in each IS.
  sorted_interaction_sessions = sorted(
    slot_base_layout.sessions_layout.keys(),
    key=lambda interaction_session: interaction_session.start_time)

  # Assign alignment only to the members in the newly added ISs.
  for interaction_session in added_interaction_sessions:
    if interaction_session in slot_base_layout.sessions_layout:
      forerunning_interaction_sessions = getForerunningInteractionSessions(
        interaction_session, sorted_interaction_sessions, is_sorted=True)

      session_layout = slot_base_layout.sessions_layout[interaction_session]
      # Assign positions to static lines
      static_lines = session_layout.static_lines
      if len(static_lines) > 0:
        sessions_in_slot = Set(slot_base_layout.slots[session_layout.slot])
        proceeding_sessions = Set(
            interaction_session.proceeding_interaction_sessions)
        common_sessions = getCommonInteractionSession(
          sessions_in_slot, proceeding_sessions)
        assert len(common_sessions) == 1, 'ERROR...'
        proceeding_interaction_session = common_sessions[0]
        proceeding_session_layout = (
            slot_base_layout.sessions_layout[proceeding_interaction_session])
        bottom_pos = None
        top_pos = None
        proceeding_layout_of_the_static_characters = dict()
        for member in static_lines:
          previous_pos = proceeding_session_layout.layout[member]
          assert previous_pos != None, 'Error...'
          proceeding_layout_of_the_static_characters[member] = previous_pos
          if bottom_pos == None or bottom_pos > previous_pos:
            bottom_pos = previous_pos
          if top_pos == None or top_pos < previous_pos:
            top_pos = previous_pos
        members_ASC = [k for v, k in sorted(((v, k) for k, v in
          proceeding_layout_of_the_static_characters.items()), reverse=False)]

        # Test out from bottom to top.
        minimum_penalty = len(static_lines)
        best_layout = dict()
        for i in range(bottom_pos, (top_pos - len(static_lines) + 2)):
          penalty = 0
          tmp_layout = dict()
          for idx, member in enumerate(members_ASC):
            tmp_layout[member] = (i+idx)
            if tmp_layout[member] != proceeding_layout_of_the_static_characters[member]:
              penalty += 1
          if penalty < minimum_penalty:
            minimum_penalty = penalty
            best_layout = tmp_layout.copy()
        assert len(best_layout) == len(static_lines), 'Error, %d %d' % (
            len(best_layout), len(static_lines))
        for member in best_layout:
          session_layout.layout[member] = best_layout[member]

      # Get bottom and top position in the current layout.
      bottom_pos = None
      top_pos = None
      for member in session_layout.layout:
        member_pos = session_layout.layout[member]
        if member_pos != None:
          if bottom_pos == None or member_pos < bottom_pos:
            bottom_pos = member_pos
          if top_pos == None or member_pos > top_pos:
            top_pos = member_pos
      if bottom_pos == None and top_pos == None:
        bottom_pos = 1
        top_pos = 0

      # Assign positions to rising lines
      rising_lines = session_layout.rising_lines
      previous_positions = dict()
      for tmp_is in forerunning_interaction_sessions:
        previous_session_layout = slot_base_layout.sessions_layout[tmp_is]
        previous_slot = previous_session_layout.slot
        if previous_slot < session_layout.slot:
          previous_layout = previous_session_layout.layout
          for member in rising_lines:
            if member in previous_layout:
              previous_pos = previous_layout[member]
              previous_positions[member] = previous_pos + 1000 * previous_slot
      rising_character_from_top_to_bottom = sorted(
        previous_positions.iteritems(),
        key=lambda (k,v): (v,k), reverse=True)

      for member, previous_position in rising_character_from_top_to_bottom:
        session_layout.layout[member] = bottom_pos - 1
        bottom_pos = bottom_pos - 1

      # Assign positions to dropping lines
      dropping_lines = session_layout.dropping_lines
      previous_positions = dict()
      for tmp_is in forerunning_interaction_sessions:
        previous_session_layout = slot_base_layout.sessions_layout[tmp_is]
        previous_slot = previous_session_layout.slot
        if previous_slot > session_layout.slot:
          previous_layout = previous_session_layout.layout
          for member in dropping_lines:
            if member in previous_layout:
              previous_pos = previous_layout[member]
              previous_positions[member] = previous_pos + 1000 * previous_slot
      dropping_character_from_bottom_to_top = sorted(
        previous_positions.iteritems(), key=lambda (k,v): (v,k))

      for member, previous_position in dropping_character_from_bottom_to_top:
        session_layout.layout[member] = top_pos + 1
        top_pos = top_pos + 1

      # Assign positions to emerging lines
      emerging_lines = session_layout.emerging_lines
      emerging_lines_will_rise = emerging_lines['will_rise']
      emerging_lines_will_drop = emerging_lines['will_drop']
      emerging_lines_will_die = emerging_lines['will_die']
      for member in emerging_lines_will_rise:
        session_layout.layout[member] = top_pos + 1
        top_pos = top_pos + 1
      for member in emerging_lines_will_drop:
        session_layout.layout[member] = bottom_pos - 1
        bottom_pos = bottom_pos - 1
      for member in emerging_lines_will_die:
        session_layout.layout[member] = bottom_pos - 1
        bottom_pos = bottom_pos - 1
  return


# Copy slot base layout of previous timestep into the current one.
def insertSlotBaseLayoutInfo(previous_slot_base_layout, slot_base_layout):
  if previous_slot_base_layout:
    previous_sessions_layout = previous_slot_base_layout.sessions_layout
    current_sessions_layout = slot_base_layout.sessions_layout
    for IS in previous_sessions_layout:
      prev_s_layout = previous_sessions_layout[IS]
      curr_s_layout = current_sessions_layout[IS]
      # Copy SessionLayout in to the current layout.
      for member, val in prev_s_layout.layout.items():
        curr_s_layout.layout[member] = val
      curr_s_layout.static_lines = prev_s_layout.static_lines.copy()
      curr_s_layout.rising_lines = prev_s_layout.rising_lines.copy()
      curr_s_layout.dropping_lines = prev_s_layout.dropping_lines.copy()
      curr_s_layout.emerging_lines = prev_s_layout.emerging_lines.copy()
  return


def rearrangeLineSegments(slot_base_layout, added_interaction_sessions):
  if len(added_interaction_sessions) > 0:
    classifyLineSegments(slot_base_layout, added_interaction_sessions)
    assignMemberAlignment(slot_base_layout, added_interaction_sessions)
  return 1


def generateSlotSegments(
    slot_base_layout, added_interaction_sessions, previous_slot_segments,
    time_steps, slot_idx_mapping=None):
  """Returns a new SlotSegments object and... """

  # Initialize slot segments.
  slot_segments = DS.SlotSegments(len(slot_base_layout.slots))
  sessions_layout = slot_base_layout.sessions_layout

  # Container for mapping the ISs in the last timestep to their new slot segments.
  # key: InteractionSession, value: the new SlotSegment.
  slotsegments_of_latest_ISs = {} 

  # Container for mapping the previous SlotSegments to the new SlotSegments
  # key: Previous SlotSegment, value: new SlotSegment.
  mapping_prev_ss_to_new_ss = {}

  # Remember the max id_number for the previous SlotSegments for assigning
  # new id_numbers to the new SlotSegments.
  max_id_number = -1

  # Container for keeping track of the ISs that are already assigned to SlotSegments.
  registered_ISs = set()

  # Copy previous SlotSegments into the new SlotSegments.
  if previous_slot_segments:
    for prev_slot_idx, prev_segment_list in previous_slot_segments.slot_segments.items():
      # Get the new slot index for this SlotSegment.
      new_slot_idx = prev_slot_idx
      if slot_idx_mapping:
        new_slot_idx = slot_idx_mapping[prev_slot_idx]

      # Construct the new SlotSegment for each previous SlotSegment.
      for prev_slot_segment in prev_segment_list:
        # Register all InteractionSessions in the SlotSegment.
        registered_ISs.update(prev_slot_segment.interaction_sessions)

        # Insert values from the previous SlotSegment in the new SlotSegment.
        id_number = prev_slot_segment.id_number
        max_id_number = max(id_number, max_id_number)
        slot_segment_clone = DS.SlotSegment(id_number)
        slot_segment_clone.slot = new_slot_idx
        for IS in prev_slot_segment.interaction_sessions:
          session_layout = sessions_layout[IS]
          slot_segment_clone.setInteractionSession(IS, session_layout)

        # Clone KL values from previous SlotSegment to the new SlotSegment.
        slot_segment_clone.KL['K'] = prev_slot_segment.KL['K']
        slot_segment_clone.KL['L'] = prev_slot_segment.KL['L']
        slot_segment_clone.KL['constraints'] = (
            prev_slot_segment.KL['constraints'].copy())

        # Remap the constraints in KL from previous SlotSegments to the
        # corresponding new SlotSegments. 
        # NOTE(ytanahashi): Although the mapping_prev_ss_to_new_ss is not
        # completed in this iteration, since it is constructed slot by slot,it
        # has all SlotSegments that are in the constraints already registered.
        for old_key, old_val in slot_segment_clone.KL['constraints'].items():
          new_key = mapping_prev_ss_to_new_ss[old_key]
          del slot_segment_clone.KL['constraints'][old_key]
          slot_segment_clone.KL['constraints'][new_key] = old_val

        # If the new SlotSegment includes an InteractionSession which has been
        # updated in the current time step, update the KL values.
        if slot_segment_clone.ending_time == time_steps:
          last_IS = slot_segment_clone.interaction_sessions[-1]
          slotsegments_of_latest_ISs[last_IS] = slot_segment_clone
          # DEBUG_CODE(ytanahashi): The last InteractionSession in the
          # SlotSegment should have the same end time as the SlotSegment's ending time.
          """
          assert last_IS.end_time == slot_segment_clone.ending_time
          """
          # Only update KL, if it has not already been updated by previous process.
          if slot_segment_clone.KL['last_timestep'] < time_steps:
            slot_segment_clone.updateKL(last_IS)

        # Insert the new SlotSegment to the SlotSegments object.
        slot_segments.slot_segments[new_slot_idx].append(slot_segment_clone)

        # Map the previous SlotSegment to the new SlotSegment.
        mapping_prev_ss_to_new_ss[prev_slot_segment] = slot_segment_clone

    # Remap the constraints in KL from previous SlotSegments to the corresponding new SlotSegments.
    # NOTE(ytanahashi): This code is depreciated.
    '''
    for slot_idx, segment_list in slot_segments.slot_segments.items():
      for slot_segment in segment_list:
        for old_key, old_val in slot_segment.KL['constraints'].items():
          new_key = mapping_prev_ss_to_new_ss[old_key]
          del slot_segment.KL['constraints'][old_key]
          slot_segment.KL['constraints'][new_key] = old_val
    '''

    # DEBUG_CODE(ytanahashi): All previous slot segments need to be mapped to a new slot segment.
    """
    for prev_slot_idx, prev_segment_list in previous_slot_segments.slot_segments.items():
      for slot_segment in prev_segment_list:
        for old_key in slot_segment.KL['constraints']:
          assert old_key in mapping_prev_ss_to_new_ss
    """

  # Construct new SlotSegment or Extend previous SlotSegment for the 
  # InteractionSessions that are not registered to SlotSegments yet.
  for slot_idx, slot in enumerate(slot_base_layout.slots):
    for idx, interaction_session in enumerate(slot):
      # DEBUG_CODE(ytanahashi): All InteractionSessions should be already
      # sorted by their timings.
      """
      if idx > 0:
        assert slot[idx - 1].start_time < interaction_session.start_time
        assert slot[idx - 1].end_time == interaction_session.start_time
      """
      if interaction_session not in registered_ISs:
        # Register the InteractionSession.
        registered_ISs.add(interaction_session)

        # Get the InteractionSession's session_layout.
        session_layout = sessions_layout[interaction_session]

        # Check if the IS belongs to previously constructed SS.
        proceeding_interaction_sessions = (
            interaction_session.proceeding_interaction_sessions)
        _extending_slot_segment = False
        for proceeding_IS in proceeding_interaction_sessions:
          if proceeding_IS in slot:
            common_members = proceeding_IS.members.intersection(
                interaction_session.members)
            if len(common_members) > 0:
              slot_segment = slot_segments.belongsToSlotSegment(
                  proceeding_IS, slot_idx)
              slot_segment.setInteractionSession(interaction_session, session_layout)
              slot_segment.updateKL(interaction_session);
              slotsegments_of_latest_ISs[interaction_session] = slot_segment
              _extending_slot_segment = True
              break

        # If there is no proceeding SlotSegment for this InteractionSession,
        # construct a new SlotSegment.
        if not _extending_slot_segment:
          max_id_number += 1
          new_slot_segment = DS.SlotSegment(max_id_number)
          new_slot_segment.slot = slot_idx
          new_slot_segment.setInteractionSession(interaction_session, session_layout)
          new_slot_segment.getKL();
          slot_segments.slot_segments[slot_idx].append(new_slot_segment)
          slotsegments_of_latest_ISs[interaction_session] = new_slot_segment

  # Update Constraints.
  update_required_SS_list = slotsegments_of_latest_ISs.values()
  # If there is only 1 or less SlotSegment in this current timestep, there
  # is no need to search for constraints.
  if len(update_required_SS_list) > 1:
    sorted_loaded_IS_SS_list = sorted(
        update_required_SS_list, key=lambda ss: ss.slot)
    for idx, ss in enumerate(sorted_loaded_IS_SS_list[1:], 1):
      ss_under = sorted_loaded_IS_SS_list[idx - 1]
      top_under = ss_under.top_coordinates[time_steps - 1]
      bottom_above = ss.bottom_coordinates[time_steps - 1]
      constraint_val = (
          - top_under - CommonParameters.OFFSET - 1 + bottom_above)
      # If the SlotSegment under is already within the constraints, update the value.
      # Otherwise, register a new constraint. 
      if ss_under in ss.KL['constraints']:
        current_val = ss.KL['constraints'][ss_under]
        ss.KL['constraints'][ss_under] = min(constraint_val, current_val)
      else:
          ss.KL['constraints'][ss_under] = constraint_val

  return slot_segments


def adjustSlotSegmentsUsingCVXOPT(slot_base_layout, slot_segments, slot_layouts,
    time_steps):

  nums_of_slot_segments = 0
  for slot_number, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    for i in range(time_steps):
      slot_layouts[slot_number].setItem(i, 0, 0, 0)
    nums_of_slot_segments += len(slot_segments_in_a_slot)

  # Each slot-segment has (k * X^2 + l * X + m) cost based on where its base is.
  # Get k and l for all slot segments.
  P_vals = numpy.zeros(nums_of_slot_segments)
  q_vals = numpy.zeros(nums_of_slot_segments)
  G_vals = []
  h_vals = []
  for slot_number, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    for slot_segment in slot_segments_in_a_slot:
      id_number = slot_segment.id_number
      k = slot_segment.KL['K']
      l = slot_segment.KL['L']
      constrains = slot_segment.KL['constraints']
      P_vals[id_number] = k
      q_vals[id_number] = l
      for ss_under, constraint_val in constrains.items():
        row_vec = numpy.zeros(nums_of_slot_segments)
        id_number_under = ss_under.id_number
        row_vec[id_number] = -1
        row_vec[id_number_under] = 1
        G_vals.append(row_vec)
        h_vals.append(constraint_val)
  P = matrix(numpy.diag(P_vals), tc='d')
  q = matrix(numpy.array(q_vals), tc='d')
  G = matrix(numpy.array(G_vals), tc='d')
  h = matrix(numpy.array(h_vals), tc='d')

  sol = solvers.qp(P, q, G, h)
  bases = sol['x']

  # Register the coordinates for all SlotSegments.
  for slot_idx, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    for slot_segment in slot_segments_in_a_slot:
      # DEBUG_CODE(ytanahashi): All SlotSegment should have the correct slot attribute here.
      """
      assert slot_idx == slot_segment.slot
      """
      id_number = slot_segment.id_number
      base_val = int(numpy.ceil(bases[id_number]))
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      for t_idx in bottom_coords:
        bottom_val = bottom_coords[t_idx]
        top_val = top_coords[t_idx] + 1
        slot_layouts[slot_idx].setItem(t_idx, base_val, bottom_val, top_val)
  return


def printOutSlotSegments(slot_segments):
  print 'SLOT SEGMENTS : '
  slot_segments_perslot = slot_segments.slot_segments
  for slot_idx, ss_collection in slot_segments_perslot.items():
    print 'SLOT %d' % slot_idx
    for ss in ss_collection:
      if ss is not None:
        print ss
        print 'Bottom: \t', ss.bottom_coordinates
        print 'Top: \t', ss.top_coordinates
  return


def removeWhiteSpace(slot_base_layout, slot_layouts, time_steps,
    added_interaction_sessions, previous_slot_segments, slot_idx_mapping):
  s_t = time()
  slot_segments = generateSlotSegments(slot_base_layout,
      added_interaction_sessions, previous_slot_segments, time_steps, slot_idx_mapping)
  e_t = time()
  print 'Generating ss took %.2f seconds' % (e_t - s_t)
  s_t = time()
  adjustSlotSegmentsUsingCVXOPT(slot_base_layout, slot_segments, slot_layouts, time_steps)
  e_t = time()
  print 'adjustss took %.2f seconds' % (e_t - s_t)
  return slot_segments


def evaluateLayoutNew(layout, slot_base_layout, time_steps, modified_interaction_sessions, detail_evals = None):
  if layout == None:
    return None

  all_members = layout.keys()
  # Real crossovers.
  crossover_count = 0
  for diff_IS in modified_interaction_sessions:
    start_time = diff_IS.start_time
    end_time = diff_IS.end_time
    # Get deviations.
    #for member_i in diff_IS.members:
    for member_i in all_members:
      prev_crossover = 0
      next_crossover = 0
      prev_y_coord_i = None
      if start_time - 1 in layout[member_i]:
        prev_y_coord_i = layout[member_i][start_time - 1]
      curr_y_coord_i = None
      if start_time in layout[member_i]:
        curr_y_coord_i = layout[member_i][start_time]
      next_y_coord_i = None
      if end_time in layout[member_i]:
        next_y_coord_i = layout[member_i][end_time]
      for member_j in all_members:
        prev_y_coord_j = None
        if start_time - 1 in layout[member_j]:
          prev_y_coord_j = layout[member_j][start_time - 1]
        curr_y_coord_j = None
        if start_time in layout[member_j]:
          curr_y_coord_j = layout[member_j][start_time]
        next_y_coord_j = None
        if end_time in layout[member_j]:
          next_y_coord_j = layout[member_j][end_time]

        prev_diff = 0
        if prev_y_coord_i is not None and prev_y_coord_j is not None:
          prev_diff = prev_y_coord_i - prev_y_coord_j
        curr_diff = 0
        if curr_y_coord_i is not None and curr_y_coord_j is not None:
          curr_diff = curr_y_coord_i - curr_y_coord_j
        next_diff = 0
        if next_y_coord_i is not None and next_y_coord_j is not None:
          next_diff = next_y_coord_i - next_y_coord_j
        if prev_diff * curr_diff < 0:
          prev_crossover += 1
        if next_diff * curr_diff < 0:
          next_crossover += 1
      crossover_count += (prev_crossover + next_crossover)

  # White space
  all_positions = []
  for layout_vals in layout.values():
    position_list = layout_vals.values()
    all_positions += position_list
  screen_top = max(all_positions)
  screen_bottom = min(all_positions)
  screen_height = screen_top - screen_bottom

  '''
  # White space
  screen_height = 0
  screen_top = None
  screen_bottom = None
  for member in layout:
    position_ary = layout[member].values()
    top_val = max(position_ary)
    bottom_val = min(position_ary)
    if screen_top is None:
      screen_top = top_val
    else:
      screen_top = max(screen_top, top_val)

    if screen_bottom is None:
      screen_bottom = bottom_val
    else:
      screen_bottom = min(screen_bottom, bottom_val)
  '''
  #rint crossover_count, screen_height
  return (crossover_count, screen_height)


def evaluateLayout(layout, slot_base_layout, time_steps, detail_evals = None):
  # Definition :
  # layout[member][time_step] == the y coordinate of the member at the time_step

  # Prepare the object for inserting detailed evaluation.
  if detail_evals is not None:
    for IS in slot_base_layout.sessions_layout:
      detail_evals[IS] = {'deviation': 0, 'crossovers': 0, 'white_space': 0}

  if layout == None:
    #rint "in evaluateLayout, layout is None"
    return -1

  member_deviations = {}
  for member in layout.keys():
    member_deviations[member] = 0

  # Count deviations agains slots.
  overall_deviations = 0
  sessions_layout = slot_base_layout.sessions_layout
  for IS, session_layout in sessions_layout.items():
    incoming_deviation = 0
    # Get current IS's slot.
    current_slot = session_layout.slot
    # Get proceeding ISs.
    proceeding_ISs = IS.proceeding_interaction_sessions
    # Check any slot-base deviations occur between the proceeding ISs and
    # current IS.
    for proceeding_IS in proceeding_ISs:
      proceeding_session_layout = sessions_layout[proceeding_IS]
      previous_slot = proceeding_session_layout.slot
      if previous_slot != current_slot:
        #slot_deviation = 1 + (float(abs(current_slot - previous_slot)) /
        #    len(slot_base_layout.slots))
        slot_deviation = 1
        #slot_deviation = abs(current_slot - previous_slot)
        #slot_deviation = sqrt(abs(current_slot - previous_slot))
        common_members = IS.members.intersection(proceeding_IS.members)
        for common_member in common_members:
          incoming_deviation += slot_deviation
          member_deviations[common_member] += slot_deviation
          # Add deviation to detailed evals.
          if detail_evals:
            detail_evals[proceeding_IS]['deviation'] += slot_deviation
    overall_deviations += incoming_deviation
    if detail_evals:
      detail_evals[IS]['deviation'] += incoming_deviation

  # Count crossovers.
  member_time_crossovers = {}
  crossovers = 0
  members = layout.keys()
  for time_step in range(1, time_steps):
    for i in range(len(members) - 1):
      for j in range(i, len(members)):
        try:
          previous_i = layout[members[i]][time_step - 1]
          previous_j = layout[members[j]][time_step - 1]
          current_i = layout[members[i]][time_step]
          current_j = layout[members[j]][time_step]
          if (previous_i - previous_j) * (current_i - current_j) < 0:
            crossovers += 1
            key_i = str((members[i], time_step))
            key_j = str((members[j], time_step))
            if key_i not in member_time_crossovers:
              member_time_crossovers[key_i] = 0
            if key_j not in member_time_crossovers:
              member_time_crossovers[key_j] = 0
            member_time_crossovers[key_i] += 1
            member_time_crossovers[key_j] += 1
        except:
          # Either i or j is not in the time steps
          pass

  if detail_evals:
    for IS in sessions_layout.keys():
      members = IS.members
      enter_t = IS.start_time
      exit_t = IS.end_time
      for member in members:
        # enter
        key_enter = str((member, enter_t))
        if key_enter in member_time_crossovers.keys():
          detail_evals[IS]['crossovers'] += member_time_crossovers[key_enter]
        # exit
        key_exit = str((member, exit_t))
        if key_exit in member_time_crossovers.keys():
          detail_evals[IS]['crossovers'] += member_time_crossovers[key_exit]

  # Count visualization space.
  screen_height = 0
  screen_top = None
  screen_bottom = None
  for member in layout:
    position_ary = layout[member].values()
    top_val = max(position_ary)
    bottom_val = min(position_ary)
    if screen_top == None:
      screen_top = top_val
    else:
      screen_top = max(screen_top, top_val)

    if screen_bottom == None:
      screen_bottom = bottom_val
    else:
      screen_bottom = min(screen_bottom, bottom_val)
  screen_height = screen_top - screen_bottom


  fitness = (overall_deviations * FITTNESS_WEIGHT['deviation'] + crossovers *
      FITTNESS_WEIGHT['crossover'] + screen_height *
      FITTNESS_WEIGHT['whitespace'])
  '''
  print 'Deviations: %d\nCrossovers: %d\nScreen: %d ~ %d\nFitness %d\n\n' % (overall_deviations, crossovers, screen_bottom, screen_top, fitness)
  '''
  return fitness


def decodeSequence(sequence, interaction_sessions):
  slot_count = max(sequence) + 1
  slot_base_layout = DS.SlotBaseLayout(slot_count)
  for idx, seq_value in enumerate(sequence):
    interaction_session = interaction_sessions[idx]
    _valid_layout = slot_base_layout.setInteractionSessionToSlot(
        interaction_session, seq_value)
    if _valid_layout == False:
      return None
  return slot_base_layout


def generateLayout(sequence, data, added_interaction_sessions,
    previous_slot_base_layout, previous_slot_segments):
  slot_count = max(sequence) + 1
  layout = None
  slot_base_layout = decodeSequence(sequence, data['interaction_sessions'])

  if slot_base_layout == None:
    # No feasible layout with this slot sequence.
    return None, None, None

  # Insert previous results into slot_base_layout.
  insertSlotBaseLayoutInfo(previous_slot_base_layout, slot_base_layout)

  # Adjust the line segments in the new ISs.
  s_t = time()
  rearrangeLineSegments(slot_base_layout, added_interaction_sessions)
  e_t = time()
  print 'Rearraning tool %.2f seconds' % (e_t - s_t)

  slot_layouts = [DS.SlotLayout(data['time_step']) for i in range(
    slot_count)]

  # Slot index re-mapped.
  slot_idx_mapping = None
  if previous_slot_base_layout:
    slot_idx_mapping = {}
    for IS in previous_slot_base_layout.sessions_layout:
      prev_session_layout = previous_slot_base_layout.sessions_layout[IS]
      curr_session_layout = slot_base_layout.sessions_layout[IS]
      slot_idx_mapping[prev_session_layout.slot] = curr_session_layout.slot
  slot_segments = removeWhiteSpace(slot_base_layout, slot_layouts,
      data['time_step'], added_interaction_sessions, previous_slot_segments,
      slot_idx_mapping)

  ## TODO(yuzuru) Need to delete this debug output
  y_coords = dict()
  time_step = data['time_step']
  for interaction_session in slot_base_layout.sessions_layout:
    session_layout = slot_base_layout.sessions_layout[interaction_session]
    start_time = interaction_session.start_time
    end_time = interaction_session.end_time
    layout = session_layout.layout
    slot_number = session_layout.slot
    slot_layout = slot_layouts[slot_number]
    for member in layout:
      if member not in y_coords:
        y_coords[member] = dict()
      for time_step in range(start_time, end_time):
        #bottom_base, height = slot_layout.layout[time_step]
        base, bottom_val, top_val = slot_layout.layout[time_step]
        y_coords[member][time_step] = layout[member] + base 
  return (y_coords, slot_base_layout, slot_segments)


def evaluateSequences(
    seq_pool, data, fitness_cache, previous_slot_base_layout,
    previous_slot_segments):
  # Extract the newly added interaction sessions.
  added_interaction_sessions = []
  if previous_slot_base_layout:
    for IS in data['interaction_sessions']:
      if IS not in previous_slot_base_layout.sessions_layout:
        added_interaction_sessions.append(IS)
  else:
    added_interaction_sessions = data['interaction_sessions'][:]

  time_step = data['time_step']
  best_seq = None
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  best_fitness = None
  for seq in seq_pool:
    seq_hash = hash(str(seq))
    if seq_hash not in fitness_cache:
      layout, slot_base_layout, slot_segments = generateLayout(seq, data,
        added_interaction_sessions, previous_slot_base_layout,
        previous_slot_segments)
      fitness = evaluateLayout(layout, slot_base_layout, time_step)
      #crossover_count, screen_height = evaluateLayoutNew(layout, slot_base_layout, time_step, [])
      #fitness = crossover_count
      fitness_cache[seq_hash] = fitness
      if fitness >= 0:
        if fitness < best_fitness or best_fitness == None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq

  return (best_layout, best_fitness,best_seq, best_slot_base_layout,
      best_slot_segments)


def evaluateSequencesUsingHeuristics(
    seq_pool, data, fitness_cache, previous_slot_base_layout,
    previous_slot_segments, modified_interaction_sessions):

  # Initialize variables.
  seq_length = len(seq_pool[0])
  time_step = data['time_step']
  interaction_sessions = data['interaction_sessions']
  IS_to_seq_idx = dict(zip(interaction_sessions, range(len(interaction_sessions))))
 
  modified_start_time = None
  modified_end_time = None
  for IS in modified_interaction_sessions:
    if modified_start_time is None:
      modified_start_time = IS.start_time
    else:
      modified_start_time = min(modified_start_time, IS.start_time)
    if modified_end_time is None:
      modified_end_time = IS.end_time
    else:
      modified_end_time = max(modified_end_time, IS.end_time)

  # Get relevant ISs.
  #s_t = time()
  relevant_IS_idx_list = []
  for IS_idx in range(seq_length):
    IS = interaction_sessions[IS_idx]
    start_time = IS.start_time
    end_time = IS.end_time
    if end_time >= modified_start_time - 1 and start_time <= modified_end_time:
      relevant_IS_idx_list.append(IS_idx)
  #e_t = time()
  #rint 'Getting relevant IS took %.2f secnods' % (e_t - s_t)

  # Extract the newly added interaction sessions.
  #s_t = time()
  added_interaction_sessions = []
  if previous_slot_base_layout:
    #for IS in interaction_sessions:
    for IS in modified_interaction_sessions:
      if IS not in previous_slot_base_layout.sessions_layout:
        added_interaction_sessions.append(IS)
  else:
    added_interaction_sessions = data['interaction_sessions'][:]
  #e_t = time()
  #rint 'Getting added IS took %.2f seconds' % (e_t - s_t)

  #s_t = time() 
  # Compute heuristical fitness.
  seq_heuristical_fitness = []
  for seq in seq_pool:
    # Renew member_to_slot.
    member_to_slot = {}
    #for IS_idx, slot_idx in enumerate(seq):
    for IS_idx in relevant_IS_idx_list:
      IS = interaction_sessions[IS_idx]
      slot_idx = seq[IS_idx]
      for member in IS.members:
        if member not in member_to_slot:
          member_to_slot[member] = {}
        for time_idx in range(IS.start_time, IS.end_time):
          member_to_slot[member][time_idx] = slot_idx
    # Get local eval for each diff IS.
    diff_IS_evals = {}
    for diff_IS in modified_interaction_sessions:
      start_time = diff_IS.start_time
      end_time = diff_IS.end_time
      prev_time_idx = start_time - 1
      curr_time_idx = start_time
      next_time_idx = end_time
      diff_IS_idx = IS_to_seq_idx[diff_IS]

      # Get deviations.
      slot_base_deviation_count = 0
      slot_base_deviations = {}
      curr_slot_idx = seq[diff_IS_idx]
      _is_independent_IS = True
      for member in diff_IS.members:
        prev_slot_idx = None
        if prev_time_idx in member_to_slot[member]:
          prev_slot_idx = member_to_slot[member][prev_time_idx]
        assert curr_slot_idx == member_to_slot[member][curr_time_idx]
        next_slot_idx = None
        if next_time_idx in member_to_slot[member]:
          next_slot_idx = member_to_slot[member][next_time_idx]
        prev_deviation = 0
        if prev_slot_idx is not None:
          _is_independent_IS = False
          prev_deviation = abs(prev_slot_idx - curr_slot_idx)
          if prev_deviation > 0:
            slot_base_deviation_count += 1
        next_deviation = 0
        if next_slot_idx is not None:
          _is_independent_IS = False
          next_deviation = abs(next_slot_idx - curr_slot_idx)
          if next_deviation > 0:
            slot_base_deviation_count += 1
        slot_base_deviations[member] = prev_deviation + next_deviation
      # If the IS has no connection to other ISs, cast them to out skirts.
      if _is_independent_IS:
        for member in diff_IS.members:
          from_top = abs(max(seq) - curr_slot_idx)
          from_bottom = abs(min(seq) - curr_slot_idx)
          deviation_penalty = min(from_top, from_bottom)
          slot_base_deviations[member] = deviation_penalty
      # Get crossovers.
      slot_base_crossovers = {}
      for member_i in diff_IS.members:
        prev_crossover = 0
        next_crossover = 0
        possible_additional_crossover = 0
        prev_slot_idx_i = None
        if prev_time_idx in member_to_slot[member_i]:
          prev_slot_idx_i = member_to_slot[member_i][prev_time_idx]
        curr_slot_idx_i = None
        if curr_time_idx in member_to_slot[member_i]:
          curr_slot_idx_i = member_to_slot[member_i][curr_time_idx]
        next_slot_idx_i = None
        if next_time_idx in member_to_slot[member_i]:
          next_slot_idx_i = member_to_slot[member_i][next_time_idx]
        for member_j in member_to_slot:
          if member_j is not member_i:
            prev_slot_idx_j = None
            if prev_time_idx in member_to_slot[member_j]:
              prev_slot_idx_j = member_to_slot[member_j][prev_time_idx]
            curr_slot_idx_j = None
            if curr_time_idx in member_to_slot[member_j]:
              curr_slot_idx_j = member_to_slot[member_j][curr_time_idx]
            next_slot_idx_j = None
            if next_time_idx in member_to_slot[member_j]:
              next_slot_idx_j = member_to_slot[member_j][next_time_idx]

            # Get differentials between these characters.
            prev_diff = None
            if prev_slot_idx_i is not None and prev_slot_idx_j is not None:
              prev_diff = prev_slot_idx_i - prev_slot_idx_j
            curr_diff = None 
            if curr_slot_idx_i is not None and curr_slot_idx_j is not None:
              curr_diff = curr_slot_idx_i - curr_slot_idx_j
            next_diff = None
            if next_slot_idx_i is not None and next_slot_idx_j is not None:
              next_diff = next_slot_idx_i - next_slot_idx_j

            #rint member_i, curr_slot_idx_i, next_slot_idx_i, member_j, curr_slot_idx_j, next_slot_idx_j, (prev_diff, curr_diff, next_diff)
            if prev_diff is not None and curr_diff is not None:
              if prev_diff * curr_diff < 0:
                prev_crossover += 1
              elif prev_diff == 0:
                possible_additional_crossover += 1
            if next_diff is not None and curr_diff is not None:
              if next_diff * curr_diff < 0:
                next_crossover += 1
              elif curr_diff == 0:
                possible_additional_crossover += 1
        min_crossover = prev_crossover + next_crossover
        max_crossover = min_crossover + possible_additional_crossover
        slot_base_crossovers[member_i] = (min_crossover, max_crossover)

      IS_min_crossover = sum([val[0] for val in slot_base_crossovers.values()])
      IS_max_crossover = sum([val[1] for val in slot_base_crossovers.values()])

      diff_IS_evals[diff_IS] = (slot_base_deviation_count,
          sum(slot_base_deviations.values()), IS_min_crossover, IS_max_crossover)
    min_max_crossover = min([val[3] for val in diff_IS_evals.values()])
    for diff_IS in diff_IS_evals:
      dev, s_dev, min_val, max_val = diff_IS_evals[diff_IS]
      if min_val <= min_max_crossover:
        diff_IS_evals[diff_IS] = (dev, s_dev, min_max_crossover)
      else:
        diff_IS_evals[diff_IS] = (dev, s_dev, min_max_crossover + 1)

    overall_h_deviation_count = 0
    overall_h_deviations = 0
    overall_h_crossovers = 0
    for diff_IS, diff_evals in diff_IS_evals.items():
      deviation_count, deviations, crossovers = diff_evals
      overall_h_deviation_count += deviation_count
      overall_h_deviations += deviations
      overall_h_crossovers += crossovers
    #TODO(ytanahashi): weight shold be given more consideration.
    #overall_h_deviations = 0
    #heuristical_fitness = (overall_h_deviation_count, overall_h_deviations,
    #    overall_h_crossovers)
    #heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers,
    #    overall_h_deviations)
    heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers)
    seq_heuristical_fitness.append(heuristical_fitness)

  # Get a sorted index list for the heuristical evaluation results.  
  sorted_heuristic_eval_seq_idx = sorted(range(len(seq_pool)),
      key=lambda k: seq_heuristical_fitness[k])
  # Get the best heuristical evaluation.
  best_heuristical_fitness = seq_heuristical_fitness[sorted_heuristic_eval_seq_idx[0]]
  # Generate new sequence pool based on the heuristical evaluation.
  new_seq_pool = []
  for seq_idx in sorted_heuristic_eval_seq_idx:
    h_fitness = seq_heuristical_fitness[seq_idx]
    seq = seq_pool[seq_idx]
    if h_fitness == best_heuristical_fitness:
      new_seq_pool.append(seq)
    else:
      break
  #new_seq_pool = new_seq_pool[:1]
  #e_t = time() 
  #rint 'HEURISTIC TOOK %.2f sec' % (e_t - s_t)

  # Eavluation the sequence pool.
  best_seq = None
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  best_fitness = None
  #s_t = time()
  for seq in new_seq_pool:
    if str(seq) not in fitness_cache:
      #ss_t = time()
      layout, slot_base_layout, slot_segments = generateLayout(seq, data,
        added_interaction_sessions, previous_slot_base_layout,
        previous_slot_segments)
      #ee_t = time()
      #rint 'genLayout took %.2f second' % (ee_t - ss_t)
      #ss_t = time()
      #fitness = evaluateLayout(layout, slot_base_layout, time_step)
      crossover_count, screen_height = evaluateLayoutNew(layout,
          slot_base_layout, time_step, modified_interaction_sessions)
      fitness = (h_fitness[0], crossover_count, screen_height)
      #ee_t = time()
      #rint 'evalLayout took %.2f second' % (ee_t - ss_t)
      fitness_cache[str(seq)] = fitness
      if fitness is not None:
        if fitness < best_fitness or best_fitness is None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq
  #e_t = time()
  #rint 'Evaluation %d new_seq took %.2f seconds' % (len(new_seq_pool), e_t - s_t)
  if best_fitness:
    best_fitness = sum(best_fitness)
  return (best_layout, best_fitness, best_seq, best_slot_base_layout,
      best_slot_segments)


def evaluateSequencesUsingHeuristicsMiddleModified(seq_pool, data, fitness_cache,
    previous_slot_base_layout, previous_slot_segments,
    modified_interaction_sessions, current_fitness, new=True):

  # Initialize variables.
  seq_length = len(seq_pool[0])
  time_step = data['time_step']
  interaction_sessions = data['interaction_sessions']
  IS_to_seq_idx = dict(zip(interaction_sessions, range(len(interaction_sessions))))
 
  modified_start_time = None
  modified_end_time = None
  for IS in modified_interaction_sessions:
    if modified_start_time is None:
      modified_start_time = IS.start_time
    else:
      modified_start_time = min(modified_start_time, IS.start_time)
    if modified_end_time is None:
      modified_end_time = IS.end_time
    else:
      modified_end_time = max(modified_end_time, IS.end_time)

  # Get relevant ISs.
  #s_t = time()
  relevant_IS_idx_list = []
  for IS_idx in range(seq_length):
    IS = interaction_sessions[IS_idx]
    start_time = IS.start_time
    end_time = IS.end_time
    if end_time >= modified_start_time - 1 and start_time <= modified_end_time:
      relevant_IS_idx_list.append(IS_idx)
  #e_t = time()
  #rint 'Getting relevant IS took %.2f secnods' % (e_t - s_t)


  # Extract the newly added interaction sessions.
  #s_t = time()
  added_interaction_sessions = []
  if new:
    added_interaction_sessions = modified_interaction_sessions[:]
  '''
  if previous_slot_base_layout:
    #for IS in interaction_sessions:
    for IS in modified_interaction_sessions:
      if IS not in previous_slot_base_layout.sessions_layout:
        added_interaction_sessions.append(IS)
  else:
    added_interaction_sessions = data['interaction_sessions'][:]
  '''
  #e_t = time()
  #rint 'Getting added IS took %.2f seconds' % (e_t - s_t)

  #s_t = time() 
  # Compute heuristical fitness.
  seq_heuristical_fitness = []
  for seq in seq_pool:
    # Renew member_to_slot.
    member_to_slot = {}
    #for IS_idx, slot_idx in enumerate(seq):
    for IS_idx in relevant_IS_idx_list:
      IS = interaction_sessions[IS_idx]
      slot_idx = seq[IS_idx]
      for member in IS.members:
        if member not in member_to_slot:
          member_to_slot[member] = {}
        for time_idx in range(IS.start_time, IS.end_time):
          member_to_slot[member][time_idx] = slot_idx

    # Get local eval for each diff IS.
    diff_IS_evals = {}
    for diff_IS in modified_interaction_sessions:
      start_time = diff_IS.start_time
      end_time = diff_IS.end_time
      prev_time_idx = start_time - 1
      curr_time_idx = start_time
      next_time_idx = end_time
      diff_IS_idx = IS_to_seq_idx[diff_IS]

      # Get deviations.
      slot_base_deviation_count = 0
      slot_base_deviations = {}
      curr_slot_idx = seq[diff_IS_idx]
      _is_independent_IS = True
      for member in diff_IS.members:
        prev_slot_idx = None
        if prev_time_idx in member_to_slot[member]:
          prev_slot_idx = member_to_slot[member][prev_time_idx]
        assert curr_slot_idx == member_to_slot[member][curr_time_idx]
        next_slot_idx = None
        if next_time_idx in member_to_slot[member]:
          next_slot_idx = member_to_slot[member][next_time_idx]
        prev_deviation = 0
        if prev_slot_idx is not None:
          _is_independent_IS = False
          prev_deviation = abs(prev_slot_idx - curr_slot_idx)
          if prev_deviation > 0:
            slot_base_deviation_count += 1
        next_deviation = 0
        if next_slot_idx is not None:
          _is_independent_IS = False
          next_deviation = abs(next_slot_idx - curr_slot_idx)
          if next_deviation > 0:
            slot_base_deviation_count += 1
        slot_base_deviations[member] = prev_deviation + next_deviation
      # If the IS has no connection to other ISs, cast them to out skirts.
      if _is_independent_IS:
        for member in diff_IS.members:
          from_top = abs(max(seq) - curr_slot_idx)
          from_bottom = abs(min(seq) - curr_slot_idx)
          deviation_penalty = min(from_top, from_bottom)
          slot_base_deviations[member] = deviation_penalty
      # Get crossovers.
      slot_base_crossovers = {}
      #for member_i in member_to_slot:
      for member_i in diff_IS.members:
        prev_crossover = 0
        next_crossover = 0
        possible_additional_crossover = 0
        prev_slot_idx_i = None
        if prev_time_idx in member_to_slot[member_i]:
          prev_slot_idx_i = member_to_slot[member_i][prev_time_idx]
        curr_slot_idx_i = None
        if curr_time_idx in member_to_slot[member_i]:
          curr_slot_idx_i = member_to_slot[member_i][curr_time_idx]
        next_slot_idx_i = None
        if next_time_idx in member_to_slot[member_i]:
          next_slot_idx_i = member_to_slot[member_i][next_time_idx]
        for member_j in member_to_slot:
          if member_j is not member_i:
            prev_slot_idx_j = None
            if prev_time_idx in member_to_slot[member_j]:
              prev_slot_idx_j = member_to_slot[member_j][prev_time_idx]
            curr_slot_idx_j = None
            if curr_time_idx in member_to_slot[member_j]:
              curr_slot_idx_j = member_to_slot[member_j][curr_time_idx]
            next_slot_idx_j = None
            if next_time_idx in member_to_slot[member_j]:
              next_slot_idx_j = member_to_slot[member_j][next_time_idx]

            # Get differentials between these characters.
            prev_diff = None
            if prev_slot_idx_i is not None and prev_slot_idx_j is not None:
              prev_diff = prev_slot_idx_i - prev_slot_idx_j
            curr_diff = None 
            if curr_slot_idx_i is not None and curr_slot_idx_j is not None:
              curr_diff = curr_slot_idx_i - curr_slot_idx_j
            next_diff = None
            if next_slot_idx_i is not None and next_slot_idx_j is not None:
              next_diff = next_slot_idx_i - next_slot_idx_j

            #rint member_i, curr_slot_idx_i, next_slot_idx_i, member_j, curr_slot_idx_j, next_slot_idx_j, (prev_diff, curr_diff, next_diff)
            if prev_diff is not None and curr_diff is not None:
              if prev_diff * curr_diff < 0:
                prev_crossover += 1
              elif prev_diff == 0:
                possible_additional_crossover += 1
            if next_diff is not None and curr_diff is not None:
              if next_diff * curr_diff < 0:
                next_crossover += 1
              elif curr_diff == 0:
                possible_additional_crossover += 1
        min_crossover = prev_crossover + next_crossover
        max_crossover = min_crossover + possible_additional_crossover
        slot_base_crossovers[member_i] = (min_crossover, max_crossover)

      IS_min_crossover = sum([val[0] for val in slot_base_crossovers.values()])
      IS_max_crossover = sum([val[1] for val in slot_base_crossovers.values()])

      #rint diff_IS, curr_slot_idx, 'crossover min max', IS_min_crossover, IS_max_crossover

      #diff_IS_evals[diff_IS] = (slot_base_deviation_count, sum(
      #    slot_base_deviations.values()))
      diff_IS_evals[diff_IS] = (slot_base_deviation_count,
          sum(slot_base_deviations.values()), IS_min_crossover, IS_max_crossover)
    min_max_crossover = min([val[3] for val in diff_IS_evals.values()])
    min_min_crossover = min([val[2] for val in diff_IS_evals.values()])
    for diff_IS in diff_IS_evals:
      dev, s_dev, min_val, max_val = diff_IS_evals[diff_IS]
      if min_val <= min_max_crossover:
        diff_IS_evals[diff_IS] = (dev, s_dev, min_min_crossover)
      else:
        diff_IS_evals[diff_IS] = (dev, s_dev, min_min_crossover + 1)

    overall_h_deviation_count = 0
    overall_h_deviations = 0
    overall_h_crossovers = 0
    for diff_IS, diff_evals in diff_IS_evals.items():
      deviation_count, deviations, crossovers = diff_evals
      overall_h_deviation_count += deviation_count
      overall_h_deviations += deviations
      overall_h_crossovers += crossovers
    #TODO(ytanahashi): weight shold be given more consideration.
    #overall_h_deviations = 0
    #heuristical_fitness = (overall_h_deviation_count, overall_h_deviations,
    #    overall_h_crossovers)
    #heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers,
    #    overall_h_deviations)
    heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers)
    print 'FITNESS....', heuristical_fitness
    seq_heuristical_fitness.append(heuristical_fitness)

  # Get a sorted index list for the heuristical evaluation results.  
  sorted_heuristic_eval_seq_idx = sorted(range(len(seq_pool)),
      key=lambda k: seq_heuristical_fitness[k])
  # Get the best heuristical evaluation.
  best_heuristical_fitness = seq_heuristical_fitness[sorted_heuristic_eval_seq_idx[0]]
  # Return None if the best_heuristical_fitness is worse than the original fitness.
  original_fitness = (current_fitness['deviation'], current_fitness['crossovers'])
  if original_fitness <= best_heuristical_fitness:
    return None, None, None, None, None

  # Generate new sequence pool based on the heuristical evaluation.
  new_seq_pool = []
  for seq_idx in sorted_heuristic_eval_seq_idx:
    h_fitness = seq_heuristical_fitness[seq_idx]
    seq = seq_pool[seq_idx]
    if h_fitness == best_heuristical_fitness:
      new_seq_pool.append(seq)
    else:
      break
  #new_seq_pool = new_seq_pool[:1]
  #e_t = time() 
  #rint 'HEURISTIC TOOK %.2f sec' % (e_t - s_t)

  # Eavluation the sequence pool.
  best_seq = None
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  best_fitness = None

  #s_t = time()
  for seq in new_seq_pool:
    if str(seq) not in fitness_cache:
      #ss_t = time()
      #layout, slot_base_layout, slot_segments = generateLayout(seq, data,
      #  added_interaction_sessions, previous_slot_base_layout,
      #  previous_slot_segments)
      layout, slot_base_layout, slot_segments = (
          LayoutFromScratchAlgorithm.generateLayout(seq, data))
      #ee_t = time()
      #rint 'genLayout took %.2f second' % (ee_t - ss_t)
      #ss_t = time()
      #fitness = evaluateLayout(layout, slot_base_layout, time_step)
      crossover, white = evaluateLayoutNew(layout, slot_base_layout, time_step, modified_interaction_sessions)
      fitness = (best_heuristical_fitness[0], crossover, white)
      #ee_t = time()
      #rint 'evalLayout took %.2f second' % (ee_t - ss_t)
      fitness_cache[str(seq)] = fitness
      if fitness is not None:
        if fitness < best_fitness or best_fitness is None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq
  #e_t = time()
  #rint 'Evaluation %d new_seq took %.2f seconds' % (len(new_seq_pool), e_t - s_t)
  if best_fitness:
    best_fitness = sum(best_fitness)
  return (best_layout, best_fitness, best_seq, best_slot_base_layout,
      best_slot_segments)
