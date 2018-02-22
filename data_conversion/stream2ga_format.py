import sys
from sets import Set

use = '''Generate the correct input format to GA.
Usage:
    stream2ga_format.py -i=./stream_inception.txt -o:./ga_inception.txt
    required:
        -i = input filename
    optional:
        -o = output filename

'''

class InteractionSession:
    def __init__(self, serial_id, start_time, end_time, members):
        self.serial_id = serial_id
        self.start_time = start_time
        self.end_time = end_time
        self.members = members

    def checkIsExtendedSession(self, new_session):
        if set(new_session.members) == set(self.members):
            if new_session.start_time == self.end_time+1 or new_session.end_time-1 == self.start_time:
                return True
        return False

    def extendSession(self, new_session):
        if new_session.start_time == self.end_time+1:
            self.end_time = new_session.end_time
        elif new_session.end_time-1 == self.start_time:
            self.start_time = new_session.start_time

    def output(self):
        member = ""
        for idx in xrange(len(self.members)):
            member += self.members[idx]
            if idx < len(self.members)-1:
                member += ','
        member = "["+member+"]"
        result = "Name\t:\t%s_%s\n" % (member,self.start_time)
        result += "Id\t:\t%s\n" % self.serial_id
        result += "Start\t:\t%s\n" % self.start_time
        result += "End\t:\t%s\n" % self.end_time
        result += "Members\t:\t%s\n" % member
        return result

def main(argv):
    # Input file name.
    iflnm = ''
    oflnm = './'
    for arg in argv:
        ary = arg.split('=')
        if ary[0] == '-i':
            iflnm = ary[1]
        elif ary[0] == '-o':
            oflnm = ary[1]

    if iflnm == '':
        print use
        return

    ifl = open(iflnm)
    # scan member names
    names = []
    for line in ifl:
        groups = line.strip('\n').split('\t')
        for group in groups:
            members = group.split(',')
            for name in members:
                if name not in names:
                    names.append(name)
    name_table = dict()
    name_count = 0
    for name in names:
        name_table[name] = str(name_count)
        name_count += 1
    print name_table

    sessions = []
    time = 1
    serial_id = 0
    ifl = open(iflnm)
    for line in ifl:
        groups = line.strip('\n').split('\t')
        for group in groups:
            members = group.split(',')
            member_ids = []
            for name in members:
                member_ids.append(name_table[name])
            new_session = InteractionSession(serial_id, time, time, member_ids)
            sessions.append(new_session)
            serial_id += 1
        time += 1

    for session1 in sessions:
        for session2 in sessions:
            if session1.checkIsExtendedSession(session2):
                session1.extendSession(session2)
                sessions.remove(session2)

    new_serial_id = 0
    for session in sessions:
        session.serial_id = new_serial_id
        new_serial_id += 1
        print session.output()


if __name__ == '__main__':
  main(sys.argv[1:])
