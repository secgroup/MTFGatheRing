from rvor_functions import *
import threading
from random import randrange

# nodes_robots[i] = j means robot j is over node i
#               0   1   2   3   4
#nodes_robots = [3,  2,  0,  1,  0]
## set the number of nodes of the ring
#nbr_nodes = len(nodes_robots)

nbr_nodes = 5
# robots_positions[i] = j means robot i+1 is on node j
# robot ids start from 1, not 0, see number on brick
# robot indices     1   2   3
#robots_positions = [0,  3,  1]
#robots_positions = [0,  4,  2]
robots_positions = [1,  3,  4]

id_M = 3
nbr_honest_robots = len(robots_positions) - 1 # all robots except M

gathered_robots = [0, 0]


# MAC address of brick bluetooth adapter, see BD address of hciconfig command
hostMACAddress = '00:17:EC:03:17:C2'
# arbitrary port, but clients must use the same port
port = 3
backlog = 1
size = 32

# map a bluetooth port with the id of the relative robot ID (see number on brick)
# as many entries as nbr of robots
addresses_ids = {'00:17:EC:03:87:1B': 1, '00:17:EC:03:2C:70': 2}

class myThread (threading.Thread):
    def __init__(self, thread_id, client_socket):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.client_socket = client_socket

    def run(self):
        print ("Thread for robot " + str(self.thread_id) + " starts")
        receive_data(self.thread_id, self.client_socket)
        print ("Exiting " + str(self.thread_id))

def receive_data(thread_id, client_socket):
    try:
        while True:
            direction = client_socket.recv(size)

            #print(str(thread_id) + ' sends:')

            # int_direction = 1 means clockwise, 0 means counterclockwise
            int_direction = int.from_bytes(direction, byteorder='big')
            # 1 remains 1, but 0 becomes -1 so that we can easily compute next node
            int_direction = int_direction + (int_direction - 1)

            next_node = (robots_positions[thread_id-1] + int_direction) % nbr_nodes;

            can_move = False
            print('\n')
            #print(int_direction)
            print('Can robot ' + str(thread_id) + ' move from node ' + str(robots_positions[thread_id-1]) + ' to node ' + str(next_node) + '?')

            # begin critical section (test and set of robot position)
            # with true parameter, thread wait for the lock untill it is available
            position_lock.acquire(True)
    
            # check if honest robot will bump against M
            # if no, update its current position
            if next_node != robots_positions[id_M-1]:
                can_move = True
                robots_positions[thread_id-1] = next_node

            # end of critical section
            position_lock.release()            

            if can_move:
                print('Yes, robot ' + str(thread_id) + ' can')
            else:
                print('No, robot ' + str(thread_id) + ' can not')
            print('\n')

            #else: # robot is M, the malicious one
                ## get the list of robots that are over the node required by M
                #blocking_robots = [x for x in robots_positions if x == next_node]
                ## if this list is empty M can move
                #can_move = ( len(blocking_robots) == 0 )

            # convert boolean variable to byte and then send it
            can_move = int(can_move).to_bytes(1, byteorder='big')
            client_socket.send(can_move)
    except:
        gathered_robots[thread_id-1] = 1
        print("Closing socket")
        client_socket.close()

def robots_gathered():
    return sum(gathered_robots) == nbr_honest_robots

# True = clockwise
def random_direction():
    print('choose a direction')
    # randrange(3) = {0,1,2}
    return randrange(3) < 2 # 2/3 of probability to choose clockwise

def can_I_move(clockwise_direction):
    
    # from boolean to int
    int_direction = int(clockwise_direction)
    # from 0,1 to -1,1
    int_direction = int_direction + (int_direction - 1)
    next_node = (robots_positions[id_M-1] + int_direction) % nbr_nodes;

    print('\n')
    print('Can I move from node ' + str(robots_positions[id_M-1]) + ' to node ' + str(next_node) + '?')

    can_move = False
    # begin critical section (test and set of robot position)
    # with true parameter, thread wait for the lock untill it is available
    position_lock.acquire(True)

    # get the list of robots that are over the node required by M
    # (in robots_positions there is also M position, but this is always different from next node)
    blocking_robots = [x for x in robots_positions if x == next_node]
    # if this list is empty M can move
    if len(blocking_robots) == 0:
        can_move = True
        robots_positions[id_M-1] = next_node

    position_lock.release()

    if can_move:
        print('Yes, I can')
    else:
        print('No, I can not')
    print('\n')

    return can_move

s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.bind((hostMACAddress,port))
s.listen(backlog)

position_lock = threading.Lock()
# accept is a blocking function
# address[0] = bluetooth id of client
# address[1] = port of the comunication channel

print('wait for honest robots to start ...')
client_socket_1, address_1 = s.accept()
#print(address_1[0])
robot_id = addresses_ids[address_1[0]]
print('robot ' + str(robot_id) + ' connected')

thread_1 = myThread(robot_id, client_socket_1)
thread_1.start()

client_socket_2, address_2 = s.accept()
#print(address_2[0])
robot_id = addresses_ids[address_2[0]]
print('robot ' + str(robot_id) + ' connected')

thread_2 = myThread(robot_id, client_socket_2)
thread_2.start()

# all the robots are connected
# and all the relative threads have been created
# send a notify message to each robot, so that it can start
start = (1).to_bytes(1, byteorder='big') # a simple byte message containing number 1
client_socket_1.send(start)
client_socket_2.send(start)

# Add threads to thread list
#threads = []
#threads.append(thread_1)
#threads.append(thread_2)

# we assume M moved in CW direction,
# that is it is in the internal ring
clockwise_direction = True

#state = directions_states[clockwise_direction]
#state = 'move'
#print('\t' + 'state: ' + str(state).upper())
#previous_state = state


while( not robots_gathered() ):

    # if it is possible, escape in CW direction
    if can_I_move(True):
        cross_marker()
        move_on_edge( int(time()), False )
        sleep(2)
    # otherwise wait a while
    else:
        sleep(5)

print('honest robots gathered\nstop')

# Wait for all threads to complete
#for t in threads:
    #t.join()

# close the listener socket when all the client exit
s.close()

