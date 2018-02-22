
import sys
import numpy
import random
from sets import Set
import DataStructure as DS

OBJECTIVE_SLOPE = 1.5
SLOTS = 50
OFFSET = 4
POPULATION = 1000
FINAL_GENERATION = 5 #1500
MUTATION_RATE = 0.6  # Below 1.0
FITTNESS_WEIGHT = {'deviation':1,
                   'crossover':1,
                   'whitespace':1}
ELITE_POPULATION = int(POPULATION * 0.5 + 0.5)
JOIN_THRESHOLD = 0.51


def loadData(iflnm):
    #print "loadData"
    (time_step, character_count, character_index_dict, location_index_dict,
     interaction_sessions) = loadInteractionSessions(iflnm)
    registerConnections(interaction_sessions)

    characters = dict()
    for character_name in character_index_dict:
        character_id = character_index_dict[character_name]
        character = DS.Character(character_name, character_id)
        characters[character_id] = character

    data = {'time_step': time_step,
            'characters': characters,
            'interaction_sessions': interaction_sessions}
    return data

def registerConnections(interaction_sessions):
    for i in range(len(interaction_sessions)):
        interaction_session_i = interaction_sessions[i]
        for j in range(i+1, len(interaction_sessions)):
            interaction_session_j = interaction_sessions[j]
            if interaction_session_i.start_time == interaction_session_j.end_time:
                interaction_session_i.proceeding_interaction_sessions.append(interaction_session_j)
                interaction_session_j.following_interaction_sessions.append(interaction_session_i)
            if interaction_session_i.end_time == interaction_session_j.start_time:
                interaction_session_j.proceeding_interaction_sessions.append(interaction_session_i)
                interaction_session_i.following_interaction_sessions.append(interaction_session_j)
    return


def loadInteractionSessions(iflnm):

    time_count = 0
    node_count = 0
    interaction_session_count = 0
    location_count = 0
    node_index_dict = dict()
    location_index_dict = dict()
    interaction_session_ary = []

    ifl = open(iflnm)
    for i in range(5):
        line = ifl.readline()
        ary = line.split('=')
        if ary[0].strip() == 'TIME_COUNT':
            time_count = int(ary[1])
        elif ary[0].strip() == 'NODE_COUNT':
            node_count = int(ary[1])
        elif ary[0].strip() == 'INTERACTION_SESSION_COUNT':
            interaction_session_count = int(ary[1])
        elif ary[0].strip() == 'LOCATION_COUNT':
            location_count = int(ary[1])
        elif ary[0].strip() == 'WEIGHTS':
            print 'Warning : Sorry this script does not take weight into account... \n Ignoring : %s' % line
        else:
            print 'error : %s' % line
            sys.exit(1)

    ## Get node names
    line = ifl.readline().strip().strip('}')
    ary = line.split(',')
    assert len(ary) == node_count
    for tmp_name_val in ary:
        [tmp_name, tmp_val] = tmp_name_val.split(':')
        name = tmp_name[ tmp_name.index('\'')+1: tmp_name.rindex('\'')]
        val = int(tmp_val)
        node_index_dict[name] = val

    ## Get location names
    line = ifl.readline().strip().strip('}')
    ary = line.split(',')
    assert len(ary) == location_count
    for tmp_name_val in ary:
        [tmp_name, tmp_val] = tmp_name_val.split(':')
        name = tmp_name[ tmp_name.index('\'')+1: tmp_name.rindex('\'')]
        val = int(tmp_val)
        location_index_dict[name] = val

    ## Get interaction sessions
    for is_idx in range(interaction_session_count):
        name = ifl.readline().split(':')[1].strip()
        id_number = int(ifl.readline().split(':')[1].strip())
        start = int(ifl.readline().split(':')[1].strip())
        end = int(ifl.readline().split(':')[1].strip())
        members_str = ifl.readline().split(':')[1].strip().strip('[]').split(',')
        location = -1
        try:
            location = int(ifl.readline().split(':')[-1].strip())
        except ValueError:
            location = -1
        ifl.readline()
        members = [int(i) for i in members_str]
        new_is = DS.InteractionSession(id_number, start, end, name, location)
        new_is.addMembers(members)
        interaction_session_ary.append(new_is)

    ifl.close()

    return (time_count, node_count, node_index_dict, location_index_dict, interaction_session_ary)


def populateGenomes(population, slots_count, genome_length):
    genome_pool = []
    for i in range(population):
        genome = [random.randint(0,slots_count-1) for i in range(genome_length)]
        genome_pool.append(genome)
    return genome_pool


def decodeGenome(genome, interaction_sessions):
    #print genome

    slot_base_layout = DS.SlotBaseLayout(SLOTS)
    for idx, genome_value in enumerate(genome):
        interaction_session = interaction_sessions[idx]
        _valid_layout = slot_base_layout.setInteractionSessionToSlot(interaction_session, genome_value)
        if _valid_layout == False:
            return None
    return slot_base_layout


def classifyProceedingLineSegments(slot_base_layout):

    for interaction_session in slot_base_layout.sessions_layout:
        session_layout = slot_base_layout.sessions_layout[interaction_session]
        proceeding_interaction_sessions = interaction_session.proceeding_interaction_sessions

        for proceeding_interaction_session in proceeding_interaction_sessions:
            #print "classifyProceedingLineSegments:"
            #print interaction_session.toString()
            #print proceeding_interaction_session.toString()

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


def getForerunningInteractionSessions(subject_interaction_session, interaction_sessions, is_sorted=False):


    sorted_interaction_sessions = []
    if is_sorted == False:
        sorted_interaction_sessions = sorted(interaction_sessions, key=lambda interaction_session: interaction_session.start_time)
    else:
        sorted_interaction_sessions = interaction_sessions[:]

    subject_is_idx = sorted_interaction_sessions.index(subject_interaction_session)
    tmp_forerunning_interaction_sessions = sorted_interaction_sessions[:subject_is_idx]
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


def rearrangeLineSegments(slot_base_layout):

    classifyLineSegments(slot_base_layout)
    assignMemberAlignment(slot_base_layout)
    return 1


def generateSlotSegments(slot_base_layout):

    sessions_layout = slot_base_layout.sessions_layout
    slot_segments = DS.SlotSegments(SLOTS)
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
                new_slot_segment = DS.SlotSegment()
                new_slot_segment.setInteractionSession(interaction_session, session_layout)
                slot_segments.slot_segments[slot_idx].append(new_slot_segment)
    return slot_segments


def adjustSlotSegments(slot_segments, slot_layouts, time_steps):

    center_slot_idx = SLOTS / 2

    # Set center slot layout.
    for i in range(len(slot_layouts[center_slot_idx].layout)):
        slot_layouts[center_slot_idx].setItem(i, 0, 0)
    slot_segment_ary = slot_segments.slot_segments[center_slot_idx]
    for slot_segment in slot_segment_ary:
        bottom_coords = slot_segment.bottom_coordinates
        top_coords = slot_segment.top_coordinates
        for time_step in bottom_coords:
            bottom_val = bottom_coords[time_step]
            top_val = top_coords[time_step]
            height = top_val - bottom_val
            slot_layouts[center_slot_idx].setItem(time_step, bottom_val, height)

    # Set the layout for the slots above center slot.
    center_to_top = range(center_slot_idx+1, SLOTS)
    for slot_idx in center_to_top:
        # Set base to the slot directly under.
        under_slot_idx = slot_idx - 1
        for time_step in range(time_steps):
            bottom_under, height_under = slot_layouts[under_slot_idx].layout[time_step]
            assert bottom_under != None and height_under != None, 'Error...'
            slot_layouts[slot_idx].setItem(time_step, (bottom_under + height_under), 0)
            # Stack slot segments on top of one anoter
        slot_segment_ary = slot_segments.slot_segments[slot_idx]
        for slot_segment in slot_segment_ary:
            bottom_coords = slot_segment.bottom_coordinates
            top_coords = slot_segment.top_coordinates
            # Retrieve the biggest offset.
            highest_base = None
            for time_step in bottom_coords:
                bottom_val = bottom_coords[time_step]
                min_base, min_height = slot_layouts[slot_idx].layout[time_step]
                necessary_base_val = min_base - bottom_val + OFFSET
                if necessary_base_val > highest_base or highest_base == None:
                    highest_base = necessary_base_val
                    # Bump up the layout of the slot for the offset.
                #print "highest_base : %d" % highest_base
            assert highest_base != None
            for time_step in bottom_coords:
                height = top_coords[time_step] - bottom_coords[time_step] + 1
                assert height > 0, 'ERROR...'
                slot_layouts[slot_idx].setItem(time_step, highest_base, height)
                #rint current_bottom, ' --> ', new_bottom

    # Set the layout for the slots under center slot.
    center_to_bottom = range(center_slot_idx)
    center_to_bottom.reverse()
    for slot_idx in center_to_bottom:
        # Set base to the slot directly above.
        above_slot_idx = slot_idx + 1
        for time_step in range(time_steps):
            bottom_above, height_above = slot_layouts[above_slot_idx].layout[time_step]
            assert bottom_above != None and height_above != None, 'Error...'
            slot_layouts[slot_idx].setItem(time_step, bottom_above, 0)
            # Stack slot segments on top of one anoter
        slot_segment_ary = slot_segments.slot_segments[slot_idx]
        for slot_segment in slot_segment_ary:
            bottom_coords = slot_segment.bottom_coordinates
            top_coords = slot_segment.top_coordinates
            # Retrieve the biggest offset.
            lowest_base = None
            #print top_coords
            for time_step in top_coords:
                top_val = top_coords[time_step]
                #print "top_val:"
                #print top_val
                #print "slot_idx:%d, time_step:%d" % (slot_idx, time_step)
                #print slot_layouts[slot_idx].layout
                min_base, min_height = slot_layouts[slot_idx].layout[time_step]
                height = top_val - bottom_coords[time_step] + 1
                necessary_base_val = min_base - height - OFFSET
                if necessary_base_val < lowest_base or lowest_base == None:
                    lowest_base = necessary_base_val
                    # Bump up the layout of the slot for the offset.
                #print "lowest_base : %d" % lowest_base
            assert lowest_base != None, 'ERROR...'
            for time_step in bottom_coords.keys():
                height = top_coords[time_step] - bottom_coords[time_step] + 1
                assert height > 0, 'ERROR...'
                slot_layouts[slot_idx].setItem(time_step, lowest_base, height)
    return


def removeWhiteSpace(slot_base_layout, slot_layouts, time_steps):

    slot_segments = generateSlotSegments(slot_base_layout)
    #print "in removeWhiteSpace"
    #print slot_segments
    adjustSlotSegments(slot_segments, slot_layouts, time_steps)
    return


def relaxLines(y_coords, interaction_sessions):

    # Sort all interaction sessions in chronological order.
    sorted_interaction_sessions = sorted(
        interaction_sessions,
        key=lambda interaction_session: interaction_session.start_time)

    # Check any subsequent pair of interaction sessions are relaxable
    # (subset member of the other).
    for interaction_session in interaction_sessions:
        forerunning_interaction_sessions = getForerunningInteractionSessions(
            interaction_session, sorted_interaction_sessions, is_sorted=True)

        members = interaction_session.members
        for forerunning_interaction_session in forerunning_interaction_sessions:
            forerunning_members = forerunning_interaction_session.members

            # Check interaction_session is subset of forerunning_interaction_session.
            is_is_subset_of_fis = members.issubset(forerunning_members)
            # Check forerunning_interaction_session is subset of interaction_session.
            fis_is_subset_of_is = forerunning_members.issubset(members)
            error_msg = 'ERROR : Two subsequent interaction sessions should be joind in the data %s %s' % (
                interaction_session.toString(), forerunning_interaction_session.toString())
            assert is_is_subset_of_fis == False or fis_is_subset_of_is == False, error_msg

            # The right interaction session is subset of the left.
            if is_is_subset_of_fis:
                best_match_diff = None
                best_match_time_step = None
                start_time = interaction_session.start_time
                end_time = interaction_session.end_time
                diffs = []
                without_diffs = []
                slope = None
                wo_slope = None
                try:
                    for member in members:
                        member_coords = y_coords[member]
                        prev_differencial = abs(
                            member_coords[start_time] - member_coords[start_time - 1])
                        next_differencial = abs(
                            member_coords[end_time] - member_coords[end_time - 1])
                        diffs.append(prev_differencial + next_differencial)
                        without_diff = abs(member_coords[end_time] - member_coords[start_time - 1])
                        without_diffs.append(without_diff)
                    avg_diff = float(sum(diffs)) / len(diffs)
                    avg_wo_diff = float(sum(without_diffs)) / len(without_diffs)
                    duration = abs(end_time - start_time)
                    slope = avg_diff / duration
                    wo_slope = avg_wo_diff / duration
                except:
                    slope = OBJECTIVE_SLOPE
                    wo_slope = OBJECTIVE_SLOPE + 1.0

                try:
                    if duration < 3:
                        # Apply relaxation
                        for member in members:
                            member_coords = y_coords[member]
                            pos_1 = member_coords[start_time-1]
                            pos_2 = member_coords[end_time]
                            for time_step in range(start_time, end_time+1):
                                member_coords[time_step] = float(
                                    end_time - time_step)/duration * pos_1 + float(
                                    time_step - start_time)/duration * pos_2
                except:
                    pass

            elif fis_is_subset_of_is:
                best_match_diff = None
                best_match_time_step = None
                start_time = forerunning_interaction_session.start_time
                end_time = forerunning_interaction_session.end_time
                duration = abs(end_time - start_time)
                diffs = []
                without_diffs = []
                slope = None
                wo_slope = None
                try:
                    for member in members:
                        member_coords = y_coords[member]
                        prev_differencial = abs(
                            member_coords[start_time] - member_coords[start_time - 1])
                        next_differencial = abs(
                            member_coords[end_time] - member_coords[end_time - 1])
                        diffs.append(prev_differencial + next_differencial)
                        without_diff = abs(member_coords[end_time] - member_coords[start_time - 1])
                        without_diffs.append(without_diff)
                    avg_diff = float(sum(diffs)) / len(diffs)
                    avg_wo_diff = float(sum(without_diffs)) / len(without_diffs)
                    slope = avg_diff / duration
                    wo_slope = avg_wo_diff / duration
                except:
                    slope = OBJECTIVE_SLOPE
                    wo_slope = OBJECTIVE_SLOPE + 1.0

                try:
                    if duration < 3:
                        # Apply relaxation
                        for member in members:
                            member_coords = y_coords[member]
                            pos_1 = member_coords[start_time-1]
                            pos_2 = member_coords[end_time]
                            for time_step in range(start_time, end_time+1):
                                member_coords[time_step] = float(
                                    end_time - time_step)/duration * pos_1 + float(
                                    time_step - start_time)/duration * pos_2
                except:
                    pass
    return


def generateLayout(genome, data):

    layout = 0
    slot_base_layout = decodeGenome(genome, data['interaction_sessions'])
    if slot_base_layout == None:
        # No feasible layout with this genome sequence.
        return None

    rearrangeLineSegments(slot_base_layout)

    slot_layouts = [DS.SlotLayout(data['time_step']) for i in range(SLOTS)]
    removeWhiteSpace(slot_base_layout, slot_layouts, data['time_step'])


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


    relaxLines(y_coords, data['interaction_sessions'])

    ## TODO(yuzuru) Implement this.
    #removeMoreWhiteSpace()
    return y_coords


def evaluateLayout(layout, time_steps):

    # Definition :
    # layout[member][time_step] == the y coordinate of the member at the time_step

    if layout == None:
        return -1

    # Count deviations.
    overall_deviations = 0
    for member in layout:
        deviations = 0
        member_layout = layout[member]
        member_timesteps = layout[member].keys()
        for time_step_idx in range(1, len(member_timesteps)):
            previous_timestep = member_timesteps[time_step_idx - 1]
            current_timestep = member_timesteps[time_step_idx]
            previous_y = member_layout[previous_timestep]
            current_y = member_layout[current_timestep]
            if previous_y != None and current_y != None:
                if previous_y != current_y:
                    deviations += 1
        overall_deviations += deviations

    # Count crossovers.
    crossovers = 0
    members = layout.keys()
    for time_step in range(1, time_steps):
        for i in range(len(members) - 1):
            for j in range(i, len(members)):
                try:
                    previous_i = layout[members[i]][time_step-1]
                    previous_j = layout[members[j]][time_step-1]
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
        position_ary = layout[member]
        top_val = max(position_ary)
        bottom_val = min(position_ary)
        if screen_top == None:
            screen_top = top_val
        else:
            screen_top = max(screen_top, top_val)

        if screen_bottom == None:
            screen_bottom = bottom_val
        else:
            screen_bottom = max(screen_bottom, bottom_val)
    screen_height = screen_top - screen_bottom

    fittness = overall_deviations * FITTNESS_WEIGHT['deviation'] + crossovers * FITTNESS_WEIGHT['crossover'] + screen_height * FITTNESS_WEIGHT['whitespace']
    return fittness


def evaluateGenomes(genome_pool, data, fittness_cache, best_fittness):

    time_step = data['time_step']
    best_layout = None
    for genome in genome_pool:
        genome_hash = hash(str(genome))
        if genome_hash not in fittness_cache:
            layout = generateLayout(genome, data)
            fittness = evaluateLayout(layout, time_step)
            fittness_cache[genome_hash] = fittness
            if fittness >= 0:
                if fittness < best_fittness or best_fittness == None:
                    best_layout = layout
                    best_fittness = fittness
    return (best_layout, best_fittness)


def getEliteGenomes(genome_pool, fittness_cache):

    genome_fittness = [fittness_cache[hash(str(genome))] for genome in genome_pool]
    genome_idx_ASC = numpy.argsort(genome_fittness)
    elite_idx_ary = genome_idx_ASC[:ELITE_POPULATION]
    elite_genomes = []
    for idx in elite_idx_ary:
        elite_genomes.append(genome_pool[idx])
    return elite_genomes


def renewGenomes(genome_pool, fittness_cache):

    elite_genomes = getEliteGenomes(genome_pool, fittness_cache)
    new_genome_pool = elite_genomes[:]

    ## Generate the new generation pool
    while len(new_genome_pool) < POPULATION:
        [mom_genome, dad_genome] = random.sample(elite_genomes, 2)
        switches = random.sample(range(len(mom_genome)+1), 2)
        switches.sort()

        ## Switching of the gene
        [switch_idx, switch_sdx] = switches
        mom_frag = mom_genome[switch_idx:switch_sdx]
        dad_frag = dad_genome[switch_idx:switch_sdx]
        daughter_genome = []
        son_genome = []

        ## Genome crossover
        for i in range(len(mom_genome)):
            mom_val = mom_genome[i]
            dad_val = dad_genome[i]
            if i in range(switch_idx,switch_sdx):
                mom_val = dad_frag[i-switch_idx]
                dad_val = mom_frag[i-switch_idx]
            daughter_genome.append(mom_val)
            son_genome.append(dad_val)

        # Mutation of the gene
        ## Daughter
        tmp_mutation_prob = random.random()
        if tmp_mutation_prob < MUTATION_RATE:
            random_idx = random.randint(0, len(daughter_genome) - 1)
            random_val = random.randint(0, SLOTS - 1)
            daughter_genome[random_idx] = random_val

        ## Son
        tmp_mutation_prob = random.random()
        if tmp_mutation_prob < MUTATION_RATE:
            random_idx = random.randint(0,len(son_genome) - 1)
            random_val = random.randint(0, SLOTS - 1)
            son_genome[random_idx] = random_val

        new_genome_pool.append(daughter_genome)
        new_genome_pool.append(son_genome)

    return new_genome_pool[:POPULATION]


def computeLayout(data):
    genome_pool = populateGenomes(POPULATION, SLOTS, len(data['interaction_sessions']))
    fittness_cache = dict()

    best_layout, best_fittness = evaluateGenomes(genome_pool, data, fittness_cache, None)
    previous_champion_genome = None
    for generation in range(FINAL_GENERATION):
        print 'Generation %d...' % generation
        genome_pool = renewGenomes(genome_pool, fittness_cache)
        tmp_best_layout, tmp_best_fittness = evaluateGenomes(genome_pool, data, fittness_cache, best_fittness)
        if tmp_best_layout != None:
            best_layout = tmp_best_layout
            best_fittness = tmp_best_fittness
    champion_genome = getEliteGenomes(genome_pool, fittness_cache)[0]
    return best_layout



use = '''
  Require:
    -i : input file name (./Data/interaction_sessions_locations.txt)
    -o : output file name (./Data/test.txt)

'''
'''
for key, value in sorted(mydict.iteritems(), key=lambda (k,v): (v,k)):
    print "%s: %s" % (key, value)
'''


def outputLayout(oflnm, layout, data):
    time_steps = data['time_step']
    characters = data['characters']
    ofl = open(oflnm, 'w')
    for member in layout:
        member_coords = layout[member]
        ofl.write(member)
        for time_step in range(time_steps):
            ofl.write('\t')
            if time_step in member_coords:
                ofl.write('%f' % member_coords[time_step])
            else:
                ofl.write(' ')
        ofl.write('\n')
    ofl.close()
    return


def main(argv):
    iflnm = ''
    oflnm = ''
    for arg in argv:
        ary = arg.split('=')
        if ary[0] == '-i':
            iflnm = ary[1]
        elif ary[0] == '-o':
            oflnm = ary[1]
        if iflnm == '' or oflnm == '':
            print use
        else:
            # origin version
            data = loadData(iflnm)
            layout = computeLayout(data)
            #print layout
            outputLayout(oflnm, layout, data)


if __name__ == '__main__':
    main(sys.argv[1:])
