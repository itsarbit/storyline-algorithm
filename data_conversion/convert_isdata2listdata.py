import sys
from sets import Set
sys.path.append('..')
import DataStructure as DS

use = '''
  Require:
    -i : input file name (./Data/interaction_sessions_locations.txt)
    -o : output file name (./Data/list.txt)

'''
'''
for key, value in sorted(mydict.iteritems(), key=lambda (k,v): (v,k)):
    print "%s: %s" % (key, value)
'''

def loadData(iflnm):
    (time_step, character_count, character_index_dict, location_index_dict,
     interaction_sessions) = loadInteractionSessions(iflnm)

    characters = dict()
    for character_name in character_index_dict:
        character_id = character_index_dict[character_name]
        character = DS.Character(character_name, character_id)
        characters[character_id] = character

    data = {'time_step': time_step,
            'characters': characters,
            'interaction_sessions': interaction_sessions}
    return data


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


# Writes out the data into a streaming-friendly format.
def outputListData(data, oflnm):

  # Open the output file.
  ofl = open(oflnm, 'w')

  # Extract data objects.
  time_steps = data['time_step']
  characters = data['characters']
  interaction_sessions = data['interaction_sessions']

  # Initialize the output data model.
  print 'Initializing empty data entry for %d timesteps' % time_steps
  streaming_data = [[] for i in range(time_steps)]

  # Inject interaction sessions into the streaming data.
  for interaction_session in interaction_sessions:
    members = interaction_session.members
    members_names = [characters[i].name for i in members]
    start_time = interaction_session.start_time
    end_time = interaction_session.end_time
    for time_step in range(start_time, end_time):
      streaming_data[time_step].append(members_names)
    print start_time, end_time, members_names

  # Write the data into the output file.
  for time_step in range(time_steps):
    time_status = streaming_data[time_step]
    group_count = len(time_status) 
    line = ('%d' % time_step) + ('\t%s' * group_count % tuple([','.join(group) for group in time_status]))
    if time_step > 0:
      ofl.write('\n')
    ofl.write(line)

  # Close the output file.
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
        outputListData(data, oflnm)


if __name__ == '__main__':
    main(sys.argv[1:])
