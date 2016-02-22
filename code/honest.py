from rvor_functions import *

def main():

    # query the server to start
    print('connect to server')
    server_socket.connect((serverMACAddress, port))
    # wait for a response, recv is a blocking function
    # server responses only when all the robots are connected
    # (value sended by server is not important)
    server_socket.recv(buffer_size)
    #int_resp = int.from_bytes(resp, byteorder='big')

    # after that each robot uses an own counter
    # in this way all the robot operations are synchronized
    begin_time = int(time())
    print('protocol begins')

    # !!! make sure robot eyes are looking at left
    # if not, protocol does not work as expected
    init_eyes_motor(eyes_speed)

    directions_states = {True: 'cw', False: 'ccw'}
    clockwise_direction = True
    state = directions_states[clockwise_direction]

    print('\t' + 'state: ' + str(state).upper())

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    previous_state = state
    #leader = False

    while True:
        # print current state for debugging
        if (previous_state != state):
            print('\t' + 'state: ' + str(state).upper())
            previous_state = state


        # CW state
        if state == directions_states[True]:
            if (is_special_node()):
                print( 'robot is over special node' )
                cross_marker()
                # move a bit further to leave space for a a possible incoming robot
                move_on_edge(collision_distance=-1, time_out=1)
                #rotate_counterclockwise(105)
                state = 'done'

            else: # robot is not on a special node

                # check if there is a robot coming from the opposite direction
                if is_there_close_robot(20):
                    # if M is in the previous node, there is no need to do anything
                    # the robot coming from the opposite direction is blocked by M and is done
                    if not can_I_move(False):
                        print('I\'m last agent')
                        state = 'done'
                    else:
                        # this is not the special node
                        # and M is not in the previous node, so leader moves
                        # follower_init is used to follow the leader for the first time
                        # rotating over the current node and moving to the previous node
                        follower_init()
                        state = 'follower'
                        # wait for two clocks
                        # one clock is used by leader and follower to reach the previous node
                        # in the other clock leader is waiting
                        begin_time = wait_clock(begin_time, 2)

                else: # no close robot
                    print('wait for one clock')
                    begin_time = wait_clock(begin_time)

                    # check again if there is a robot coming from the opposite direction
                    if is_there_close_robot(25):
                        if not can_I_move(False):
                            print('I\'m last agent')
                            state = 'done'
                        else:
                            # the robot that becomes leader is waiting for one clock
                            # first wait with it
                            begin_time = wait_clock(begin_time)
                            # then start to follow it, as above
                            follower_init()
                            state = 'follower'
                            begin_time = wait_clock(begin_time, 2)

                    else: # no close robot after one clock
                        if (not can_I_move(True)):
                            print('robot is blocked in the last move')
                            cross_marker()

                            rotate_over_node()

                            clockwise_direction = False
                            state = directions_states[False]

                            print('direction changed, wait the end of the second clock')
                            begin_time = wait_clock(begin_time)

                        else: # robot can move
                            print('robot moves toward next node')
                            cross_marker()
                            robot_collision = move_on_edge()
                            if robot_collision:
                                state = 'done'
                            else:
                                begin_time = wait_clock(begin_time)


        # CCW state
        elif state == directions_states[False]:
            special_node = is_special_node()
            can_move = can_I_move(False)

            if special_node or not can_move:
                if special_node:
                    print( 'robot is over special node' )
                # if robot have to change direction again
                # this means it has one ore more followers and it met all the robots in the ring
                # so it becomes done
                # followers became done once they notice that leader does not move
                if not can_move:
                    print('M met twice\nstop')

                sleep(1.5) # during this time followers looks with is_leader_moving function
                # enter the node to leave space for some possible followers
                cross_marker()
                rotate_over_node(time_out=4.5)
                state = 'done'
            # robot is not on special node and it can move
            else:
                print('robot moves toward next node')
                cross_marker()
                move_on_edge(collision_distance=-1)
                print('wait the end of the first clock')
                begin_time = wait_clock(begin_time)
                print('wait for another clock')
                begin_time = wait_clock(begin_time)

        elif state == 'follower':
            #check_done, leader_moving = is_leader_moving()
            # is_leader_moving checks 2 times with eyes
            if ( not is_leader_moving() ):
                # only the second follower enter in this state
                print('I\'m the second follower')
                # wait while the other follower is moving
                sleep(2)
                move_on_edge() # stop with collision
                state = 'done'
            else:
                # complete the last part of edge
                move_on_edge(collision_distance=-1, time_to_settle=0)

                if is_special_node():
                # only the first follower enter in this state
                    print('I\'m the first follower')
                    # wait while leader is rotating over node
                    sleep(0.8)
                    # there is no space if robot has the eyes looking at right
                    #motor_m.run_to_abs_pos(position_sp = 90)
                    # once reach the marker move a bit further 
                    # to leave space for the second follower
                    cross_marker()
                    move_on_edge(collision_distance=-1, time_out=1)
                    state = 'done'
                else:
                    # follow leader
                    move_on_edge()
                    # once stopped, wait also for the clock in which leader waits
                    begin_time = wait_clock(begin_time, 2)

        elif state == 'done':
            server_socket.close()
            print('gathering')
            # 'US-SI-CM' ultra sound mode sometimes results in an error
            # that's why in protocol we use always the eyes opened
            # us.mode = 'US-SI-CM' # shut down eyes

            # exit the program
            break
            # [TODO] some errors are shown on terminal, check why


        elif state == 'stopped':
            if is_there_close_robot(140):
                print('close robot detected')
                state = 'done'
            else:
                begin_time = wait_clock(begin_time)

if __name__ == '__main__':
    main()


