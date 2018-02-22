import DataStructure as DS
import CommonParameters
from numpy import sqrt
from sets import Set
from time import time

from cvxopt import matrix
from cvxopt import solvers
import numpy
import math

FITTNESS_WEIGHT = {'deviation':5, 'crossover':5, 'whitespace':1}



def classifyProceedingLineSegments(slot_base_layout):

  for interaction_session in slot_base_layout.sessions_layout:
    session_layout = slot_base_layout.sessions_layout[interaction_session]
    proceeding_interaction_sessions = interaction_session.proceeding_interaction_sessions
    for proceeding_interaction_session in proceeding_interaction_sessions:
      proceeding_session_layout = slot_base_layout.sessions_layout[proceeding_interaction_session]
      intersecting_members = interaction_session.members.intersection(proceeding_interaction_session.members)
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



def classifyEmergingLineSegments(slot_base_layout):

  sorted_interaction_sessions = sorted(
      slot_base_layout.sessions_layout.keys(),
      key=lambda interaction_session: interaction_session.start_time)
  sorted_interaction_sessions.reverse()

  for interaction_session in sorted_interaction_sessions:
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


def classifyLineSegments(slot_base_layout):
  classifyProceedingLineSegments(slot_base_layout)
  classifyEmergingLineSegments(slot_base_layout)
  assert checkAllLinsegmentsAreClassified(slot_base_layout) == True, 'Error: Not all line segments are classified...'
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



def assignMemberAlignment(slot_base_layout):
  # This function assigns the layout for the line segments in each interaction session.
  sorted_interaction_sessions = sorted(
      slot_base_layout.sessions_layout.keys(),
      key=lambda interaction_session: interaction_session.start_time)

  #for interaction_session in slot_base_layout.sessions_layout:
  for is_idx, interaction_session in enumerate(sorted_interaction_sessions):
    forerunning_interaction_sessions = getForerunningInteractionSessions(
        interaction_session, sorted_interaction_sessions, is_sorted=True)

    session_layout = slot_base_layout.sessions_layout[interaction_session]
    # Assign positions to static lines
    static_lines = session_layout.static_lines
    if len(static_lines) > 0:
      sessions_in_slot = Set(slot_base_layout.slots[session_layout.slot])
      proceeding_sessions = Set(interaction_session.proceeding_interaction_sessions)
      common_sessions = getCommonInteractionSession(
          sessions_in_slot, proceeding_sessions)
      assert len(common_sessions) == 1, 'ERROR...'
      proceeding_interaction_session = common_sessions[0]
      proceeding_session_layout = slot_base_layout.sessions_layout[proceeding_interaction_session]
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
      members_ASC = [k for v, k in sorted(
          ((v, k) for k, v in proceeding_layout_of_the_static_characters.items()),
          reverse=False)]

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
      assert len(best_layout) == len(static_lines), 'Error, %d %d' % (len(best_layout), len(static_lines))
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


def rearrangeLineSegments(slot_base_layout):
  classifyLineSegments(slot_base_layout)
  assignMemberAlignment(slot_base_layout)
  return 1





def generateSlotSegments(slot_base_layout):
  slot_count = len(slot_base_layout.slots)
  id_number = 0

  sessions_layout = slot_base_layout.sessions_layout
  slot_segments = DS.SlotSegments(slot_count)
  slots = slot_base_layout.slots
  for slot_idx, slot in enumerate(slots):
    # Sort interaction sessions by its starting time.
    sorted_interaction_sessions = sorted(
        slot, key=lambda interaction_session: interaction_session.start_time)
    for interaction_session in sorted_interaction_sessions:
      members = interaction_session.members
      session_layout = sessions_layout[interaction_session]
      proceeding_interaction_sessions = (
          interaction_session.proceeding_interaction_sessions)
      for proceeding_interaction_session in proceeding_interaction_sessions:
        common_members = proceeding_interaction_session.members.intersection(members)
        if len(common_members) > 0:
          # These interation sessions are connected.
          proceeding_IS_slot_segment = slot_segments.belongsToSlotSegment(
              proceeding_interaction_session, slot_idx)
          if proceeding_IS_slot_segment == None:
            # These interaction sessions do not belong to the same slot.
            pass
          else:
            proceeding_IS_slot_segment.setInteractionSession(
                interaction_session, session_layout)
            break
      IS_slot_segment = slot_segments.belongsToSlotSegment(
          interaction_session, slot_idx)
      if IS_slot_segment == None:
        new_slot_segment = DS.SlotSegment(id_number)
        id_number += 1
        new_slot_segment.setInteractionSession(interaction_session, session_layout)
        slot_segments.slot_segments[slot_idx].append(new_slot_segment)
  return slot_segments






def adjustSlotSegmentsUsingCVXOPT(slot_base_layout, slot_segments, slot_layouts,
    time_steps):

  for slot_number in slot_segments.slot_segments:
    for i in range(time_steps):
      slot_layouts[slot_number].setItem(i, 0, 0, 0)

  # Each slot-segment has (k * X^2 + l * X + m) cost based on where its base is.
  # Get k and l for all slot segments.
  KL_dict = {}
  slot_segment_under = [None for i in range(time_steps)]
  nums_of_slot_segments = 0
  for slot_number, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    nums_of_slot_segments += len(slot_segments_in_a_slot)
    for slot_segment in slot_segments_in_a_slot:
      cvx_property = {'k': 0, 'l': 0, 'constraints': {}}
      k = 0
      l = 0
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates

      for t_idx in bottom_coords:
        bottom_val = bottom_coords[t_idx]
        top_val = top_coords[t_idx]
        assert top_val - bottom_val >= 0
        # Get k.
        k = k + (top_val - bottom_val + 1)
        # Get l.
        for val in range(bottom_val, top_val + 1):
          l = l + (val * 2)
        # Get constrains.
        ss_under = slot_segment_under[t_idx]
        if ss_under:
          # X_under + under_top_val + offset <= X_this + bottom_val
          constraint_val = (-ss_under.top_coordinates[t_idx]
              - CommonParameters.OFFSET - 1 + bottom_val)
          # -X_this + X_under <= bottom_val - top_val - offset == constraint_val
          if ss_under in cvx_property['constraints']:
            current_constraint = cvx_property['constraints'][ss_under]
            if constraint_val < current_constraint:
              cvx_property['constraints'][ss_under] = constraint_val
          else:
            cvx_property['constraints'][ss_under] = constraint_val

        # Update the under slot segment
        slot_segment_under[t_idx] = slot_segment
      cvx_property['k'] = k
      cvx_property['l'] = l

      id_number = len(KL_dict)
      KL_dict[slot_segment] = {'id': id_number, 'cvx': cvx_property}
      slot_segment.KL['K'] = k
      slot_segment.KL['L'] = l
      slot_segment.KL['last_timestep'] = slot_segment.ending_time
      for key, val in cvx_property['constraints'].items():
        slot_segment.KL['constraints'][key] = val



  P_vals = [0 for i in range(nums_of_slot_segments)]
  q_vals = [0 for i in range(nums_of_slot_segments)]
  G_vals = []
  h_vals = []
  for slot_number, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    for slot_segment in slot_segments_in_a_slot:
      id_number = KL_dict[slot_segment]['id']
      cvx_property = KL_dict[slot_segment]['cvx']
      k = cvx_property['k']
      l = cvx_property['l']
      constrains = cvx_property['constraints']
      P_vals[id_number] = k
      q_vals[id_number] = l
      for ss_under, constraint_val in constrains.items():
        row_vec = [0 for i in range(nums_of_slot_segments)]
        id_number_under = KL_dict[ss_under]['id']
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

  for slot_idx, slot_segments_in_a_slot in slot_segments.slot_segments.items():
    for slot_segment in slot_segments_in_a_slot:
      id_number = KL_dict[slot_segment]['id']
      base_val = int(math.ceil(bases[id_number]))
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      for t_idx in bottom_coords:
        bottom_val = bottom_coords[t_idx]
        top_val = top_coords[t_idx] + 1
        slot_layouts[slot_idx].setItem(t_idx, base_val, bottom_val, top_val)
  #print bases[0]
  return



def adjustSlotSegments(slot_base_layout, slot_segments, slot_layouts,
    time_steps):
  slot_count = len(slot_segments.slot_segments)
  bottom_slot_idx = 0
  highest_coordinate = 0

  # Register slot segments' connections.
  # key: slot_segment, value (upward connections, downward connections)
  slot_segment_connections = {}
  for slot_idx in range(slot_count):
    slot_semgnet_list = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_semgnet_list:
      up = 0
      down = 0
      IS_ary = slot_segment.interaction_sessions
      for IS in IS_ary:
        proceeding_ISs = IS.proceeding_interaction_sessions
        following_ISs = IS.following_interaction_sessions
        connecting_ISs = proceeding_ISs + following_ISs
        for c_IS in connecting_ISs:
          if c_IS in slot_base_layout.sessions_layout:
            session_layout = slot_base_layout.sessions_layout[c_IS]
            c_slot_idx = session_layout.slot
            if slot_idx < c_slot_idx:
              up += len(IS.members.intersection(c_IS.members))
            elif slot_idx > c_slot_idx:
              down += len(IS.members.intersection(c_IS.members))
      slot_segment_connections[slot_segment] = (up, down)

  # Set bottom slot layout.
  for i in range(len(slot_layouts[bottom_slot_idx].layout)):
    slot_layouts[bottom_slot_idx].setItem(i, 0, 0, 0)
  slot_segment_ary = slot_segments.slot_segments[bottom_slot_idx]
  for slot_segment in slot_segment_ary:
    bottom_coords = slot_segment.bottom_coordinates
    top_coords = slot_segment.top_coordinates
    for time_step in bottom_coords:
      bottom_val = bottom_coords[time_step]
      top_val = top_coords[time_step] + 1
      slot_layouts[bottom_slot_idx].setItem(time_step, 0, bottom_val, top_val)

  # Set the layout for the slots above bottom slot.
  bottom_to_top = range(bottom_slot_idx + 1, slot_count)
  for slot_idx in bottom_to_top:
    # Set base to the slot directly under.
    under_slot_idx = slot_idx - 1
    for time_step in range(time_steps):
      base_under, bottom_under, top_under = (
          slot_layouts[under_slot_idx].layout[time_step])
      assert (bottom_under != None and bottom_under != None and top_under != None, 'Error...')
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
        if base_under != 0 or bottom_under != 0 or top_under != 0:
          if necessary_base_val > highest_base or highest_base == None:
            highest_base = necessary_base_val
        else:
          if necessary_base_val > potential_highest_base or potential_highest_base == None:
            potential_highest_base = necessary_base_val - CommonParameters.OFFSET
      # Bump up the layout of the slot for the offset.
      if highest_base is None:
        highest_base = potential_highest_base
      assert highest_base != None
      for time_step in bottom_coords:
        bottom_val = bottom_coords[time_step]
        top_val = top_coords[time_step] + 1
        slot_layouts[slot_idx].setItem(time_step, highest_base, bottom_val,
            top_val)
        highest_coordinate = max(highest_coordinate, highest_base + top_val)


  
  lowest_coordinate = highest_coordinate
  # Set top slot layout.
  top_slot_idx = slot_count - 1
  for time_step in range(time_steps):
    base, bottom, top = slot_layouts[top_slot_idx].layout[time_step]
    slot_layouts[top_slot_idx].setItem(time_step, highest_coordinate, 0, 0)
  for slot_segment in slot_segments.slot_segments[top_slot_idx]:
    bottom_coords = slot_segment.bottom_coordinates
    top_coords = slot_segment.top_coordinates
    new_base = highest_coordinate
    for time_step in top_coords:
      top_val = top_coords[time_step] + 1
      potential_base = highest_coordinate - top_val
      new_base = min(highest_coordinate, potential_base)
    for time_step in top_coords:
      bottom_val = bottom_coords[time_step]
      top_val = top_coords[time_step] + 1
      slot_layouts[top_slot_idx].setItem(time_step, new_base, bottom_val,
          top_val)

    

  top_to_bottom = range(slot_count - 1)
  top_to_bottom.reverse()
  for slot_idx in top_to_bottom:
    above_slot_idx = slot_idx + 1
    for time_step in range(time_steps):
      base_above, bottom_above, top_above = (
          slot_layouts[above_slot_idx].layout[time_step])
      slot_layouts[slot_idx].setItem(time_step, (base_above + bottom_above), 0, 0)
    slot_segment_ary = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_segment_ary:
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      lowest_base = highest_coordinate
      potential_lowest_base = highest_coordinate
      for time_step in top_coords:
        top_val = top_coords[time_step] + 1
        bottom_val = bottom_coords[time_step]
        base_above, bottom_above, top_above = (
            slot_layouts[above_slot_idx].layout[time_step])
        necessary_base_val = (base_above + bottom_above - top_val
            - CommonParameters.OFFSET)
        lowest_base = min(lowest_base, necessary_base_val)
      assert lowest_base is not None, 'Error...'
      for time_step in bottom_coords:
        bottom_val = bottom_coords[time_step]
        top_val = top_coords[time_step] + 1
        slot_layouts[slot_idx].setItem(time_step, lowest_base, bottom_val,
            top_val)
        lowest_coordinate = min(lowest_coordinate, lowest_base + bottom_val)



  # Adjust inner slot segments.
  bottom_slot_idx = 0
  below_layer_ss_list = [None for time_idx in range(time_steps)]
  bottom_slot_segment_ary = slot_segments.slot_segments[bottom_slot_idx]
  for slot_segment in bottom_slot_segment_ary:
    for time_idx in slot_segment.bottom_coordinates:
      below_layer_ss_list[time_idx] = slot_segment

  for time_step in range(time_steps):
    base, bottom, top = slot_layouts[bottom_slot_idx].layout[time_step]
    if base == bottom == top == 0:
      new_base = lowest_coordinate 
      slot_layouts[top_slot_idx].setItem(time_step, new_base, bottom, top)

  bottom_to_top = range(1, slot_count)
  for slot_idx in bottom_to_top:
    #under_slot_idx = slot_idx - 1
    for time_step in range(time_steps):
      base, bottom, top = slot_layouts[slot_idx].layout[time_step]
    slot_segment_ary = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_segment_ary:
      up, down = slot_segment_connections[slot_segment]
      current_base, unused_bottom, unused_top = (
          slot_layouts[slot_idx].layout[slot_segment.starting_time])
      # Push down all.
      bottom_coords = slot_segment.bottom_coordinates
      top_coords = slot_segment.top_coordinates
      # Retrieve the biggest offset.
      highest_base = lowest_coordinate
      new_base = None
      for time_step in bottom_coords:
        ss_under = below_layer_ss_list[time_step]
        if ss_under is not None:
          under_slot_idx = ss_under.slot
          base_under, bottom_under, top_under = (
              slot_layouts[under_slot_idx].layout[time_step])
          bottom_val = bottom_coords[time_step]
          top_coord_under = base_under + top_under
          potential_base = (top_coord_under - bottom_val
              + CommonParameters.OFFSET)
          if new_base is None:
            new_base = potential_base
          else:
            new_base = max(new_base, potential_base)
      if new_base is not None:
        if new_base < current_base:
          assert new_base is not None
          # Push down the layout of the slot for the offset.
          for time_step in bottom_coords:
            base, bottom, top = slot_layouts[slot_idx].layout[time_step]
            slot_layouts[slot_idx].setItem(time_step, new_base, bottom, top)
      for time_idx in slot_segment.bottom_coordinates:
        below_layer_ss_list[time_idx] = slot_segment

  # Push up.
  above_layer_ss_list = [None for time_idx in range(time_steps)]
  top_slot_segment_ary = slot_segments.slot_segments[top_slot_idx]
  for slot_segment in top_slot_segment_ary:
    for time_idx in slot_segment.bottom_coordinates:
      above_layer_ss_list[time_idx] = slot_segment

  for slot_idx in top_to_bottom:
    slot_segment_ary = slot_segments.slot_segments[slot_idx]
    for slot_segment in slot_segment_ary:
      up, down = slot_segment_connections[slot_segment]
      if down < up:
        slot_idx = slot_segment.slot
        this_slot_layout = slot_layouts[slot_idx].layout
        tmp_base, tmp_bottom, tmp_top = this_slot_layout[slot_segment.starting_time]
        ss_top_coords = slot_segment.top_coordinates
        ss_bottom_coords = slot_segment.bottom_coordinates
        assert slot_idx is not None
        assert slot_idx != top_slot_idx
  
        new_base = None
        for time_idx in ss_top_coords:
          ss_above = above_layer_ss_list[time_idx]
          if ss_above is not None:
            above_slot_idx = ss_above.slot
            base_above, bottom_above, top_above = (
                slot_layouts[above_slot_idx].layout[time_idx])
            top_val = ss_top_coords[time_idx] + 1
            bottom_coord_above = base_above + bottom_above
            potential_base = bottom_coord_above - top_val - CommonParameters.OFFSET
            if new_base is None:
              new_base = potential_base
            else:
              new_base = min(new_base, potential_base)
        if new_base is not None:
          if new_base > tmp_base:
            for time_idx in ss_top_coords:
              base, bottom, top = this_slot_layout[time_idx]
              slot_layouts[slot_idx].setItem(time_idx, new_base, bottom, top)
      for time_idx in slot_segment.top_coordinates:
        above_layer_ss_list[time_idx] = slot_segment

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




def removeWhiteSpace(slot_base_layout, slot_layouts, time_steps):
  slot_segments = generateSlotSegments(slot_base_layout)
  adjustSlotSegmentsUsingCVXOPT(slot_base_layout, slot_segments, slot_layouts, time_steps)
  #adjustSlotSegments(slot_base_layout, slot_segments, slot_layouts, time_steps)
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
  print crossover_count, screen_height
  return (crossover_count, screen_height)


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
            print key_i
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




def generateLayout(genome, data):

  layout = 0
  slot_count = max(genome) + 1
  slot_base_layout = decodeSequence(genome, data['interaction_sessions'])
  if slot_base_layout == None:
    # No feasible layout with this genome sequence.
    return None, None, None

  rearrangeLineSegments(slot_base_layout)

  slot_layouts = [DS.SlotLayout(data['time_step']) for i in range(slot_count)]
  slot_segments = removeWhiteSpace(slot_base_layout, slot_layouts, data['time_step'])

  '''
  ## TODO(yuzuru) Need to delete this debug output
  y_coords = dict()
  time_steps = data['time_step']
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
        bottom_base, height = slot_layout.layout[time_step]
        y_coords[member][time_step] = layout[member] + bottom_base
  '''

  
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


  ## TODO(yuzuru) Implement this.
  #relaxLines(y_coords, data['interaction_sessions'])
  #removeMoreWhiteSpace()
  #return y_coords
  return (y_coords, slot_base_layout, slot_segments)


'''
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
  from time import time
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
'''


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


def evaluateSequencesUsingHeuristics(seq_pool, data, fitness_cache,
    previous_slot_base_layout, previous_slot_segments,
    modified_interaction_sessions):

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
  s_t = time()
  relevant_IS_idx_list = []
  for IS_idx in range(seq_length):
    IS = interaction_sessions[IS_idx]
    start_time = IS.start_time
    end_time = IS.end_time
    if end_time >= modified_start_time - 1 and start_time <= modified_end_time:
      relevant_IS_idx_list.append(IS_idx)
  e_t = time()
  print 'Getting relevant IS took %.2f secnods' % (e_t - s_t)


  # Extract the newly added interaction sessions.
  s_t = time()
  added_interaction_sessions = []
  if previous_slot_base_layout:
    #for IS in interaction_sessions:
    for IS in modified_interaction_sessions:
      if IS not in previous_slot_base_layout.sessions_layout:
        added_interaction_sessions.append(IS)
  else:
    added_interaction_sessions = data['interaction_sessions'][:]
  e_t = time()
  print 'Getting added IS took %.2f seconds' % (e_t - s_t)

  s_t = time() 
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
      diff_IS_idx = IS_to_seq_idx[diff_IS]
      # Get deviations.
      slot_base_deviation_count = 0
      slot_base_deviations = {}
      curr_slot_idx = seq[diff_IS_idx]
      _is_independent_IS = True
      for member in diff_IS.members:
        prev_slot_idx = None
        if start_time - 1 in member_to_slot[member]:
          prev_slot_idx = member_to_slot[member][start_time - 1]
        assert curr_slot_idx == member_to_slot[member][start_time]
        next_slot_idx = None
        if time_step in member_to_slot[member]:
          next_slot_idx = member_to_slot[member][time_step]
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
      for member_i in member_to_slot:
        prev_crossover = 0
        next_crossover = 0
        prev_slot_idx_i = None
        if start_time - 1 in member_to_slot[member_i]:
          prev_slot_idx_i = member_to_slot[member_i][start_time - 1]
        curr_slot_idx_i = None
        if start_time in member_to_slot[member_i]:
          curr_slot_idx_i = member_to_slot[member_i][start_time]
        next_slot_idx_i = None
        if end_time in member_to_slot[member_i]:
          next_slot_idx = member_to_slot[member_i][end_time]
        for member_j in member_to_slot:
          prev_slot_idx_j = None
          if start_time - 1 in member_to_slot[member_j]:
            prev_slot_idx_j = member_to_slot[member_j][start_time - 1]
          curr_slot_idx_j = None
          if start_time in member_to_slot[member_j]:
            curr_slot_idx_j = member_to_slot[member_j][start_time]
          next_slot_idx_j = None
          if end_time in member_to_slot[member_j]:
            next_slot_idx_j = member_to_slot[member_j][end_time]

          prev_diff = 0
          if prev_slot_idx_i is not None and prev_slot_idx_j is not None:
            prev_diff = prev_slot_idx_i - prev_slot_idx_j
          curr_diff = 0
          if curr_slot_idx_i is not None and curr_slot_idx_j is not None:
            curr_diff = curr_slot_idx_i - curr_slot_idx_j
          next_diff = 0
          if next_slot_idx_i is not None and next_slot_idx_j is not None:
            next_diff = next_slot_idx_i - next_slot_idx_j
          if prev_diff * curr_diff < 0:
            prev_crossover += 1
          if next_diff * curr_diff < 0:
            next_crossover += 1
        slot_base_crossovers[member_i] = prev_crossover + next_crossover
      diff_IS_evals[diff_IS] = (slot_base_deviation_count, sum(
          slot_base_deviations.values()), sum(slot_base_crossovers.values())) 
            
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
    heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers,
        overall_h_deviations)
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
  e_t = time() 
  print 'HEURISTIC TOOK %.2f sec' % (e_t - s_t)

  # Eavluation the sequence pool.
  best_seq = None
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  best_fitness = None
  s_t = time()
  print new_seq_pool
  for seq in new_seq_pool:
    if str(seq) not in fitness_cache:
      ss_t = time()
      layout, slot_base_layout, slot_segments = generateLayout(seq, data,
        added_interaction_sessions, previous_slot_base_layout,
        previous_slot_segments)
      ee_t = time()
      print 'genLayout took %.2f second' % (ee_t - ss_t)
      ss_t = time()
      #fitness = evaluateLayout(layout, slot_base_layout, time_step)
      fitness = evaluateLayoutNew(layout, slot_base_layout, time_step, modified_interaction_sessions)
      ee_t = time()
      print 'evalLayout took %.2f second' % (ee_t - ss_t)
      fitness_cache[str(seq)] = fitness
      if fitness is not None:
        if fitness < best_fitness or best_fitness is None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq
  e_t = time()
  print 'Evaluation %d new_seq took %.2f seconds' % (len(new_seq_pool), e_t - s_t)
  if best_fitness:
    best_fitness = sum(best_fitness)
  return (best_layout, best_fitness, best_seq, best_slot_base_layout,
      best_slot_segments)





def evaluateSequencesUsingHeuristicsMiddleModified(seq_pool, data, fitness_cache,
    previous_slot_base_layout, previous_slot_segments,
    modified_interaction_sessions, new=True):

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
  s_t = time()
  relevant_IS_idx_list = []
  for IS_idx in range(seq_length):
    IS = interaction_sessions[IS_idx]
    start_time = IS.start_time
    end_time = IS.end_time
    if end_time >= modified_start_time - 1 and start_time <= modified_end_time:
      relevant_IS_idx_list.append(IS_idx)
  e_t = time()
  print 'Getting relevant IS took %.2f secnods' % (e_t - s_t)


  # Extract the newly added interaction sessions.
  s_t = time()
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
  e_t = time()
  print 'Getting added IS took %.2f seconds' % (e_t - s_t)

  s_t = time() 
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
      diff_IS_idx = IS_to_seq_idx[diff_IS]
      # Get deviations.
      slot_base_deviation_count = 0
      slot_base_deviations = {}
      curr_slot_idx = seq[diff_IS_idx]
      _is_independent_IS = True
      for member in diff_IS.members:
        prev_slot_idx = None
        if start_time - 1 in member_to_slot[member]:
          prev_slot_idx = member_to_slot[member][start_time - 1]
        assert curr_slot_idx == member_to_slot[member][start_time]
        next_slot_idx = None
        if time_step in member_to_slot[member]:
          next_slot_idx = member_to_slot[member][time_step]
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
      for member_i in member_to_slot:
        prev_crossover = 0
        next_crossover = 0
        possible_additional_crossover = 0
        prev_slot_idx_i = None
        if start_time - 1 in member_to_slot[member_i]:
          prev_slot_idx_i = member_to_slot[member_i][start_time - 1]
        curr_slot_idx_i = None
        if start_time in member_to_slot[member_i]:
          curr_slot_idx_i = member_to_slot[member_i][start_time]
        next_slot_idx_i = None
        if end_time in member_to_slot[member_i]:
          next_slot_idx = member_to_slot[member_i][end_time]
        for member_j in member_to_slot:
          prev_slot_idx_j = None
          if start_time - 1 in member_to_slot[member_j]:
            prev_slot_idx_j = member_to_slot[member_j][start_time - 1]
          curr_slot_idx_j = None
          if start_time in member_to_slot[member_j]:
            curr_slot_idx_j = member_to_slot[member_j][start_time]
          next_slot_idx_j = None
          if end_time in member_to_slot[member_j]:
            next_slot_idx_j = member_to_slot[member_j][end_time]

          prev_diff = 0
          if prev_slot_idx_i is not None and prev_slot_idx_j is not None:
            prev_diff = prev_slot_idx_i - prev_slot_idx_j
          curr_diff = 0
          if curr_slot_idx_i is not None and curr_slot_idx_j is not None:
            curr_diff = curr_slot_idx_i - curr_slot_idx_j
          next_diff = 0
          if next_slot_idx_i is not None and next_slot_idx_j is not None:
            next_diff = next_slot_idx_i - next_slot_idx_j
          if prev_diff * curr_diff < 0:
            prev_crossover += 1
          elif prev_diff * curr_diff == 0:
            possible_additional_crossover += 1
          if next_diff * curr_diff < 0:
            next_crossover += 1
          elif next_diff * curr_diff == 0:
            possible_additional_crossover += 1
        min_crossover = prev_crossover + next_crossover
        max_crossover = min_crossover + possible_additional_crossover
        slot_base_crossovers[member_i] = (min_crossover, max_crossover)

      IS_min_crossover = sum([val[0] for val in slot_base_crossovers.values()])
      IS_max_crossover = sum([val[1] for val in slot_base_crossovers.values()])

      #diff_IS_evals[diff_IS] = (slot_base_deviation_count, sum(
      #    slot_base_deviations.values()))
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
    heuristical_fitness = (overall_h_deviation_count, overall_h_crossovers,
        overall_h_deviations)
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
  e_t = time() 
  print 'HEURISTIC TOOK %.2f sec' % (e_t - s_t)

  # Eavluation the sequence pool.
  best_seq = None
  best_layout = None
  best_slot_base_layout = None
  best_slot_segments = None
  best_fitness = None
  s_t = time()

  print 'new_seq', new_seq_pool
  for seq in new_seq_pool:
    if str(seq) not in fitness_cache:
      ss_t = time()
      layout, slot_base_layout, slot_segments = generateLayout(seq, data,
        added_interaction_sessions, previous_slot_base_layout,
        previous_slot_segments)
      ee_t = time()
      print 'genLayout took %.2f second' % (ee_t - ss_t)
      ss_t = time()
      #fitness = evaluateLayout(layout, slot_base_layout, time_step)
      fitness = evaluateLayoutNew(layout, slot_base_layout, time_step, modified_interaction_sessions)
      ee_t = time()
      print 'evalLayout took %.2f second' % (ee_t - ss_t)
      fitness_cache[str(seq)] = fitness
      if fitness is not None:
        if fitness < best_fitness or best_fitness is None:
          best_layout = layout
          best_slot_base_layout = slot_base_layout
          best_slot_segments = slot_segments
          best_fitness = fitness
          best_seq = seq
  e_t = time()
  print 'Evaluation %d new_seq took %.2f seconds' % (len(new_seq_pool), e_t - s_t)
  if best_fitness:
    best_fitness = sum(best_fitness)
  return (best_layout, best_fitness, best_seq, best_slot_base_layout,
      best_slot_segments)





