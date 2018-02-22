import DataStructure as DS
import CommonParameters
from numpy import sqrt
from sets import Set

FITTNESS_WEIGHT = {'deviation':5, 'crossover':5, 'whitespace':1}

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


def generateSlotSegments(slot_base_layout, added_interaction_sessions,
    previous_slot_segments):

  # Initialize slot segments.
  slot_count = len(slot_base_layout.slots)
  slot_segments = DS.SlotSegments(slot_count)
  sessions_layout = slot_base_layout.sessions_layout

  registered_ISs = []
  # Copy previous slot segments into the current one.
  if previous_slot_segments:
    for slot_idx in previous_slot_segments.slot_segments:
      segment_list = previous_slot_segments.slot_segments[slot_idx]
      for slot_segment in segment_list:
        registered_ISs.extend(slot_segment.interaction_sessions)
        # Insert old slot_segments in the new slot_segments.
        slot_segment_clone = DS.SlotSegment()
        slot_segment_clone.slot = slot_idx
        for IS in slot_segment.interaction_sessions:
          session_layout = sessions_layout[IS]
          slot_segment_clone.setInteractionSession(IS, session_layout)
        slot_segments.slot_segments[slot_idx].append(slot_segment_clone)

  slots = slot_base_layout.slots
  for slot_idx, slot in enumerate(slots):
    # Sort interaction sessions by its starting time.
    sorted_interaction_sessions = sorted(
      slot, key=lambda interaction_session: interaction_session.start_time)
    for idx, interaction_session in enumerate(sorted_interaction_sessions):
      #if interaction_session in added_interaction_sessions:
      if interaction_session not in registered_ISs:
        registered_ISs.append(interaction_session)
        session_layout = sessions_layout[interaction_session]
        proceeding_interaction_sessions = (
            interaction_session.proceeding_interaction_sessions)
        _extending_slot_segment = False
        for proceeding_IS in proceeding_interaction_sessions:
          if proceeding_IS in slot:
            # Check if there are any common members.
            common_members = proceeding_IS.members.intersection(
                interaction_session.members)
            # If there are common members in the interaction session directly left,
            # the slotsegment is a mere extension.
            if len(common_members) > 0:
              slot_segment = slot_segments.belongsToSlotSegment(
                  proceeding_IS, slot_idx)
              assert slot_segment
              slot_segment.setInteractionSession(interaction_session, session_layout)
              _extending_slot_segment = True
              break
        if not _extending_slot_segment:
          new_slot_segment = DS.SlotSegment()
          new_slot_segment.setInteractionSession(interaction_session, session_layout)
          slot_segments.slot_segments[slot_idx].append(new_slot_segment)

  return slot_segments


def adjustSlotSegments(slot_segments, slot_layouts, time_steps):
  slot_count = len(slot_segments.slot_segments)
  center_slot_idx = slot_count / 2

  # Initialize storage for slot segments need to be pushed up & down.
  push_up_slot_segments = []
  push_down_slot_segments = []
  # Set center slot layout.
  for i in range(len(slot_layouts[center_slot_idx].layout)):
    slot_layouts[center_slot_idx].setItem(i, 0, 0, 0)
  slot_segment_ary = slot_segments.slot_segments[center_slot_idx]
  for slot_segment in slot_segment_ary:
    bottom_coords = slot_segment.bottom_coordinates
    top_coords = slot_segment.top_coordinates
    for time_step in bottom_coords:
      bottom_val = bottom_coords[time_step]
      top_val = top_coords[time_step] + 1
      slot_layouts[center_slot_idx].setItem(time_step, 0, bottom_val, top_val)
    # All slot segments in the center slot need to be pushed up later.
    if center_slot_idx < slot_count - 1:
      slot_segment.slot = center_slot_idx
      push_up_slot_segments.append((slot_segment, 0))

  # Set the layout for the slots above center slot.
  center_to_top = range(center_slot_idx + 1, slot_count)
  for slot_idx in center_to_top:
    # Set base to the slot directly under.
    under_slot_idx = slot_idx - 1
    for time_step in range(time_steps):
      base_under, bottom_under, top_under = (
          slot_layouts[under_slot_idx].layout[time_step])
      slot_layouts[slot_idx].setItem(time_step, (base_under + top_under), 0, 0)
    # Stack slot segments on top of one another
    slot_segment_ary = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_segment_ary:
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      # Retrieve the biggest offset.
      highest_base = None
      potential_highest_base = None
      for time_step in bottom_coords:
        bottom_val = bottom_coords[time_step]
        base_under, bottom_under, top_under = (
            slot_layouts[under_slot_idx].layout[time_step])
        necessary_base_val = (base_under + top_under - bottom_val
            + CommonParameters.OFFSET)
        if base_under == bottom_under == top_under == 0:
          if potential_highest_base is None:
            potential_highest_base = necessary_base_val
          else:
            potential_highest_base = max(potential_highest_base,
                necessary_base_val)
        else:
          if highest_base is None:
            highest_base = necessary_base_val
          else:
            highest_base = max(highest_base, necessary_base_val)
      # Bump up the layout of the slot for the offset.
      if highest_base is None:
        # This indicates that the slot segment needs push up later.
        if slot_idx < slot_count - 1:
          # highest_base = potential_highest_base
          slot_segment.slot = slot_idx
          push_up_slot_segments.append((slot_segment, potential_highest_base))
        else:
          highest_base = potential_highest_base
      # If the slot segment is not push up segments, assign it on base. 
      if highest_base is not None:
        for time_step in bottom_coords:
          bottom_val = bottom_coords[time_step]
          top_val = top_coords[time_step] + 1
          slot_layouts[slot_idx].setItem(time_step, highest_base, bottom_val,
              top_val)

  # Adjust the slot layout of the slot directly above center slot.
  if center_slot_idx < slot_count - 1:
    slot_idx = center_slot_idx + 1
    for time_step in range(time_steps):
      base, bottom, top = slot_layouts[slot_idx].layout[time_step]
      if bottom == top == 0:
        if slot_idx < slot_count - 1:
          for above_slot_idx in range(slot_idx + 1, slot_count):
            base_above, bottom_above, top_above = (
                slot_layouts[above_slot_idx].layout[time_step])
            if bottom_above == top_above == 0:
              above_slot_idx += 1
              base = 0
            else:
              base = base_above + bottom_above
              break
        else:
          base = CommonParameters.OFFSET
        slot_layouts[slot_idx].setItem(time_step, base, bottom, top)

  # Push up bottom slot segments.
  push_up_slot_segments.reverse()
  for slot_segment, potential_base in push_up_slot_segments:
    print 'PUSH UP ', slot_segment.slot, ':', center_slot_idx
    for IS in slot_segment.interaction_sessions:
      print '\t', IS.toString()

    slot_idx = slot_segment.slot
    bottom_coords = slot_segment.bottom_coordinates
    top_coords = slot_segment.top_coordinates
    lowest_base = None
    for time_step in top_coords:
      top_val = top_coords[time_step] + 1
      base_above = 0
      bottom_above = 0
      top_above = 0
      for above_slot_idx in range(slot_idx + 1, slot_count):
        tmp_base_above, tmp_bottom_above, tmp_top_above = (
            slot_layouts[above_slot_idx].layout[time_step])
        if tmp_bottom_above != tmp_top_above:
          base_above = tmp_base_above
          bottom_above = tmp_bottom_above
          top_above = tmp_top_above
          break

      assert bottom_above != None and top_above != None, 'Error...'
      necessary_base_val = (base_above + bottom_above - top_val
          - CommonParameters.OFFSET)
      print base_above, bottom_above, top_above, 'N', necessary_base_val
      if base_above == bottom_above == top_above == 0:
        pass
      else:
      #if base_above != 0 or bottom_above != 0 or top_above != 0:
        if necessary_base_val < lowest_base or lowest_base is None:
          lowest_base = necessary_base_val
    # Push up the layout of the slot.
    #assert lowest_base is not None, 'Need fixing with causion...'
    if lowest_base is None:
      lowest_base = potential_base
    print 'pb', potential_base, 'lb', lowest_base
    if lowest_base is not None:
      for time_step in bottom_coords:
        bottom_val = bottom_coords[time_step]
        top_val = top_coords[time_step] + 1
        slot_layouts[slot_idx].setItem(time_step, lowest_base, bottom_val, top_val)

  # Sort out center slot layout.
  time_step_count = len(slot_layouts[center_slot_idx].layout)
  for time_step in range(time_step_count):
    base, bottom, top = slot_layouts[center_slot_idx].layout[time_step]
    if bottom == top == 0:
      for slot_idx in center_to_top:
        base, bottom, top = slot_layouts[slot_idx].layout[time_step]
        if bottom == top == 0:
          base = 0
        else:
          break
    slot_layouts[center_slot_idx].setItem(time_step, base, bottom, top)
  '''
  '''
  print 'CENTER: ', slot_layouts[center_slot_idx].layout

  # Set the layout for the slots under center slot.
  center_to_bottom = range(center_slot_idx)
  center_to_bottom.reverse()
  for slot_idx in center_to_bottom:
    # Set base to the slot directly above.
    above_slot_idx = slot_idx + 1
    for time_step in range(time_steps):
      base_above, bottom_above, height_above = (
          slot_layouts[above_slot_idx].layout[time_step])
      assert bottom_above != None and height_above != None, 'Error...'
      # Insert the height_above to avoid later confusion with the invisible center slot.
      slot_layouts[slot_idx].setItem(time_step, (base_above + bottom_above), 0,
          0)
      #slot_layouts[slot_idx].setItem(time_step, (base_above + bottom_above), 0,
      #    height_above)
    # Stack slot segments under of one anoter
    slot_segment_ary = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_segment_ary:
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      # Retrieve the biggest offset.
      lowest_base = None
      potential_lowest_base = None
      for time_step in top_coords:
        top_val = top_coords[time_step] + 1
        bottom_val = bottom_coords[time_step]
        base_above, bottom_above, top_above = (
            slot_layouts[above_slot_idx].layout[time_step])
        necessary_base_val = (base_above + bottom_above - top_val
            - CommonParameters.OFFSET)
        if base_above == bottom_above == top_above == 0:
          if potential_lowest_base is None:
            potential_lowest_base = necessary_base_val
          else:
            potential_lowest_base = min(potential_lowest_base,
                necessary_base_val)
        else:
          if lowest_base is None:
            lowest_base = necessary_base_val
          else:
            lowest_base = min(lowest_base, necessary_base_val)
      # Push down the layout of the slot for the offset.
      if lowest_base is None:
        # This indicates that the slot segment needs push down later.
        #assert slot_idx > 0, 'error.... need fixing...'
        if slot_idx > 0:
          slot_segment.slot = slot_idx
          push_down_slot_segments.append((slot_segment, potential_lowest_base))
          #lowest_base = potential_lowest_base
        else:
          lowest_base = potential_lowest_base
      if lowest_base is not None:
        for time_step in bottom_coords:
          bottom_val = bottom_coords[time_step]
          top_val = top_coords[time_step] + 1
          slot_layouts[slot_idx].setItem(time_step, lowest_base, bottom_val,
              top_val)

  # Push down top slot segments
  push_down_slot_segments.reverse()
  for slot_segment, potential_base in push_down_slot_segments:
    slot_idx = slot_segment.slot
    under_slot_idx = slot_idx - 1
    bottom_coords = slot_segment.bottom_coordinates
    top_coords = slot_segment.top_coordinates
    highest_base = None
    for time_step in bottom_coords:
      bottom_val = bottom_coords[time_step]
      base_under = 0
      bottom_under = 0
      top_under = 0
      slot_idx_range = range(slot_idx)
      slot_idx_range.reverse()
      for under_slot_idx in slot_idx_range:
        tmp_base_under, tmp_bottom_under, tmp_top_under = (
            slot_layouts[under_slot_idx].layout[time_step])
        if tmp_bottom_under != tmp_top_under:
          base_under = tmp_base_under
          bottom_under = tmp_bottom_under
          top_under = tmp_top_under
          break
      assert bottom_under != None and top_under != None, 'Error...'
      necessary_base_val = (base_under + top_under - bottom_val 
          + CommonParameters.OFFSET)
      if base_under != 0 or bottom_under != 0 or top_under != 0:
        if necessary_base_val < highest_base or highest_base is None:
          highest_base = necessary_base_val
    # Push up the layout of the slot.
    if highest_base is None:
      highest_base = potential_base
    if highest_base is not None:
      for time_step in bottom_coords:
        bottom_val = bottom_coords[time_step]
        top_val = top_coords[time_step] + 1
        slot_layouts[slot_idx].setItem(time_step, highest_base, bottom_val,
            top_val)



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
    added_interaction_sessions, previous_slot_segments):
  slot_segments = generateSlotSegments(slot_base_layout,
      added_interaction_sessions, previous_slot_segments)
  adjustSlotSegments(slot_segments, slot_layouts, time_steps)
  return slot_segments


def evaluateLayout(layout, slot_base_layout, time_steps, detail_evals = None):
  # Definition :
  # layout[member][time_step] == the y coordinate of the member at the time_step

  # Prepare the object for inserting detailed evaluation.
  if detail_evals is not None:
    for IS in slot_base_layout.sessions_layout:
      detail_evals[IS] = {'deviation': 0, 'crossovers': 0, 'white_space': 0}

  if layout == None:
    #print "in evaluateLayout, layout is None"
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
        slot_deviation = 1 + (float(abs(current_slot - previous_slot)) /
            len(slot_base_layout.slots))
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
        except:
          # Either i or j is not in the time steps
          pass

  # Count visualization space.
  screen_height = 0
  screen_top = None
  screen_bottom = None
  for member in layout:
    position_ary = layout[member].values()
    top_val = max(position_ary)
    bottom_val = min(position_ary)
    '''
    tmp_pos_line = '\t:\t'
    for t_idx in range(time_steps):
      val = ''
      if t_idx in layout[member]:
        val = '%d' % layout[member][t_idx]
      tmp_pos_line += '\t' + val
    print member, bottom_val, top_val, '(%d)' % member_deviations[member], tmp_pos_line
    '''
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
  rearrangeLineSegments(slot_base_layout, added_interaction_sessions)

  slot_layouts = [DS.SlotLayout(data['time_step']) for i in range(
    slot_count)]
  slot_segments = removeWhiteSpace(slot_base_layout, slot_layouts,
    data['time_step'], added_interaction_sessions, previous_slot_segments)

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


def evaluateSequences(seq_pool, data, fitness_cache, previous_slot_base_layout,
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
      fitness_cache[seq_hash] = fitness
      if fitness >= 0:
        if fitness < best_fitness or best_fitness == None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq
  '''
  print "BEST OF TIME %d - (%d)" % (time_step, len(seq_pool[0]))
  print "ADDED: ", data['interaction_sessions'][len(seq_pool[0]) - 1].toString()
  tmp_fitness = evaluateLayout(best_layout, best_slot_base_layout,
      time_step)
  print ""
  '''
  return (best_layout, best_fitness,best_seq, best_slot_base_layout,
      best_slot_segments)
