from sets import Set

class InteractionSession:

  def __init__(self, id_number, start_time, end_time = -1, name = '', location=-1):
    self.name = name
    self.id = id_number
    self.start_time = start_time
    if end_time < 0:
      end_time = start_time-1
    self.end_time = end_time
    self.members = Set()
    self.location= location
    self.proceeding_interaction_sessions = []
    self.following_interaction_sessions = []

  def addMembers(self, members):
    for member in members:
      self.members.add(member)
    return

  def getMemberCount(self):
    return len(self.members)

  def setEndTime(self, time):
    self.end_time = time
    return

  def matchName(self, name):
    _match = False
    self_name_hash = hash(self.name)
    name_hash = hash(name)
    if self_name_hash == name_hash:
      _match = True
    return _match

  def toString(self):
    content = ''' Name    :  %s
 Id    :  %d
 Start   :  %d
 End     :  %d
 Members   :  %s
 Location  :  %d
''' % (self.name, self.id, self.start_time, self.end_time, str(self.members), self.location)
    return content


class Character:

  def __init__(self, name, character_id, weight = 1.0):
    self.name = name
    self.character_id = character_id
    self.weight = weight

  def getId(self):
    return self.character_id


class SessionLayout:

  def __init__(self, slot_number, interaction_session):
    self.slot = slot_number
    self.layout = dict()
    for member in interaction_session.members:
      self.layout[member] = None
    self.static_lines = Set()
    self.rising_lines = Set()
    self.dropping_lines = Set()
    self.emerging_lines = {'will_rise': Set(), 'will_drop': Set(),
        'will_die': Set()}
    return

  def getClassifiedMembers(self):
    classified_members = dict()
    for member in self.static_lines:
      classified_members[member] = 'static'
    for member in self.rising_lines:
      classified_members[member] = 'rising'
    for member in self.dropping_lines:
      classified_members[member] = 'dropping'
    for member in self.emerging_lines['will_rise']:
      classified_members[member] = 'will_rise'
    for member in self.emerging_lines['will_drop']:
      classified_members[member] = 'will_drop'
    for member in self.emerging_lines['will_die']:
      classified_members[member] = 'will_die'
    return classified_members


class SlotBaseLayout:

  def __init__(self, slot_count):
    self.slots = [[] for i in range(slot_count)]
    # Key: InteractionSession, Value: SessionLayout
    self.sessions_layout = dict()
    return

  def setInteractionSessionToSlot(self, interaction_session, slot_number):
    _availability = self.checkAvailability(interaction_session, slot_number)
    if _availability == True:
      self.slots[slot_number].append(interaction_session)
      self.sessions_layout[interaction_session] = SessionLayout(slot_number, interaction_session)
    return _availability

  def checkAvailability(self, interaction_session, slot_number):
    registered_interaction_sessions = self.slots[slot_number][:]
    _availability = True
    for registered_interaction_session in registered_interaction_sessions:
      if interaction_session.start_time >= registered_interaction_session.end_time or\
         interaction_session.end_time <= registered_interaction_session.start_time:
        pass
      else:
        # These interaction sessions overlap.
        _availability = False
        break
    return _availability

  def checkAvailabilityFromTime(self, start_time, end_time, slot_number):
    registered_interaction_sessions = self.slots[slot_number][:]
    _availability = True
    for registered_interaction_session in registered_interaction_sessions:
      if (registered_interaction_session.start_time >= end_time or
        registered_interaction_session.end_time <= start_time):
        pass
      else:
        # These interaction sessions overlap.
        _availability = False
        break
    return _availability


class SlotLayout:

  def __init__(self, time_steps):
    # base, bottom, top 
    self.layout = [[None, None, None] for i in range(time_steps)]
    return

  def setItem(self, idx, base, bottom, top):
    self.layout[idx] = [base, bottom, top]
    return


class SlotSegment:

  def __init__(self, id_number):
    self.id_number = id_number
    self.slot = None
    self.interaction_sessions = []
    self.starting_time = None
    self.ending_time = None
    self.bottom_coordinates = dict()
    self.top_coordinates = dict()
    self.KL = {'K': 0, 'L': 0, 'constraints': {}, 'last_timestep': -1}
    return

  def __str__(self):
    interaction_sessions_names = ('%s||' * len(self.interaction_sessions)
      % tuple([IS.name for IS in self.interaction_sessions])).strip('||')
    ss_str = (('NAME: %s \n SLOT: ' % (interaction_sessions_names)) 
      + str(self.slot)
      + ' \t TIME ' + str(self.starting_time) + ' ~ '
      + str(self.ending_time))
    return ss_str

  #def __repr__(self):
  #  return self.__str__()

  def setInteractionSession(self, interaction_session, session_layout):
    self.interaction_sessions.append(interaction_session)
    if (self.starting_time == None or
      self.starting_time > interaction_session.start_time):
      self.starting_time = interaction_session.start_time
    if self.ending_time == None or self.ending_time < interaction_session.end_time:
      self.ending_time = interaction_session.end_time
    bottom_coord = None
    top_coord = None
    for member in session_layout.layout:
      member_coordinate = session_layout.layout[member]
      if bottom_coord == None or bottom_coord > member_coordinate:
        bottom_coord = member_coordinate
      if top_coord == None or top_coord < member_coordinate:
        top_coord = member_coordinate
    for time_step in range(
      interaction_session.start_time,
      interaction_session.end_time):
      self.bottom_coordinates[time_step] = bottom_coord
      self.top_coordinates[time_step] = top_coord
    return

  def getKL(self):
    IS_list = self.interaction_sessions
    k = 0
    l = 0
    last_timestep = -1
    for IS in IS_list:
      duration = IS.end_time - IS.start_time
      member_count = len(IS.members)
      k = k + (member_count * duration)
      top_val = self.top_coordinates[IS.start_time]
      bottom_val = self.bottom_coordinates[IS.start_time]
      l = l + (sum(range(bottom_val, top_val + 1)) * 2 * duration)
      last_timestep = max(IS.end_time, last_timestep)
    self.KL['K'] = k
    self.KL['L'] = l
    self.KL['last_timestep'] = last_timestep
    return

  def updateKL(self, IS):
    member_count = len(IS.members)
    top_val = self.top_coordinates[IS.start_time]
    bottom_val = self.bottom_coordinates[IS.start_time]
    current_k = self.KL['K']
    current_l = self.KL['L']
    self.KL['K'] = current_k + member_count
    self.KL['L'] = current_l + (sum(range(bottom_val, top_val + 1)) * 2)
    self.KL['last_timestep'] = IS.end_time
    return


class SlotSegments:

  def __init__(self, slots_count):
    self.slot_segments = dict()
    for slot_idx in range(slots_count):
      self.slot_segments[slot_idx] = []
    return

  def belongsToSlotSegment(self, interaction_session, slot_idx = None):
    if slot_idx == None:
      for slot in self.slot_segments:
        for slot_segment in slot:
          if interaction_session in slot_segment.interaction_sessions:
            return slot_segment
    else:
      slot = self.slot_segments[slot_idx]
      for slot_segment in slot:
        if interaction_session in slot_segment.interaction_sessions:
          return slot_segment
    return None
