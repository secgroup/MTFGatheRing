#from rvor_functions import move_on_edge, rotate_over_node
from robot_functions import *
from requests import post
from json import loads

def main():

    print('protocol begins')

    '''
    each clock follows these sequences of instruction:
        state = 'state name'
        set state function
        movement or rotation
        get states function
        sync clock function    
    '''

    # !!! make sure robot eyes are looking at left
    # if not, protocol does not work as expected
    init_eyes_motor(eyes_speed)

    # init values
    state = 'initial'
    special_node_reached = 0

    print('\t' + 'state: ' + str(state).upper())

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    previous_state = state

    # query the server to start
    print('connect to server')

    start()
    # after that each robot uses an own counter
    # in this way all the robot operations are synchronized
    begin_time = int(time())

    while True:
        # print current state for debugging
        if (previous_state != state):
            print('\t' + 'state: ' + str(state).upper())
            previous_state = state

        
        if state == 'initial':

            # notify to server the intention of moving
            blocked_last_move = set_node_info(state)

            if blocked_last_move:

                print('robot is blocked in last move')
                state = 'stopped'
                #turned = True
                set_node_info(state, turned=1, stopped=1)
                # move robot on the other side of the node
                # because no other robots could come from the opposite direction,
                # since M block them
                cross_marker()
                rotate_over_node()

            else: # robot moves
                cross_marker()
                # a robot may can collide with another in state done, but in this case motors stop
                move_on_edge()

                # then it "looks around" to collect the states of the other robots on the same node
                # actually, these states have been stored before, with the call of set_node_info function performed by each robot
                neighbors_states, blocked_last_move = get_node_info()

                # after that robot moved, it syncronize its clock waiting the remaining time
                begin_time = wait_clock(begin_time)

            
                # no more than one robot for a node can be in state stopped
                if len(neighbors_states) == 1 and neighbors_states[0] == 'stopped':
                    print('met a robot in state stopped')
                    state = 'done'
                    set_node_info(state, turned=1, stopped=1)
                    # move robot on the other side of the node
                    # take the place of stopped robot
                    cross_marker()
                    rotate_over_node()

                # no more than one robot in state initial can reach M,
                # without first reach a stopped robot
                elif len(neighbors_states) == 0 and blocked_last_move:
                    state = 'stopped'
                    #turned = True
                    set_node_info(state, turned=1, stopped=1)
                    # move robot on the other side of the node
                    # because no other robots could come from the opposite direction,
                    # since M block them
                    cross_marker()
                    rotate_over_node()

                # [TODO] change this condition
                elif is_special_node():
                    special_node_reached += 1
                    nbr_star_robots = get_state_robots(neighbors_states, robot_state='star')
                    if special_node_reached == 2 and nbr_star_robots == 0:
                        state = 'star'
                        # move robot in the middle of the curve
                        # because other robots could arrive from both the direction
                        # but when they arrived from the same direction, they must go straight on
                        cross_marker()
                        # [TODO]
                        # unfortunately node is small, the exact time to rotate is important
                        # to avoid robots to bump one to each other
                        rotate_over_node(time_out=4.5)

        elif state == 'stopped':
            # during this time, other robots perform a set
            sleep(2)
            neighbors_states, blocked_last_move = get_node_info()

            # no more than one robot reach a stopped robot
            if len(neighbors_states) == 1 and neighbors_states[0] == 'initial':
                print('met a robot in state initial')

                begin_time = wait_clock(begin_time)

                # a stopped robot rotated over node, so direction is changed
                # new state is set in next state
                state = 'collect'

            elif len(neighbors_states) == 1 and neighbors_states[0] == 'collect':
                print('met a robot in state collect')
                # wait a clock, during this time collect robot is rotating over the node
                begin_time = wait_clock(begin_time, nbr_clocks=2)

                # a stopped robot rotated over node, so direction is changed
                # new state is set in next state
                first_returning_robot = True
                state = 'return'
            else:
                begin_time = wait_clock(begin_time)
                '''
                elif len(neighbors_states) == 1 and neighbors_states[0] == 'check':
                    print('met a robot in state check')
                    # a stopped robot rotated over node, so direction is changed
                    #turned = True
                    state = 'return'
                '''
            # wait only if the state remain stopped, otherwise start moving, see others state
            # else:
            # begin_time = wait_clock(begin_time)

        elif state == 'collect':
            # notify to server the intention of moving
            blocked_last_move = set_node_info(state)

            if blocked_last_move:
                print('robot is blocked in last move')
                state = 'return'
                set_node_info(state, turned=1, stopped=1)
                cross_marker()
                rotate_over_node()

            else: # robot moves
                cross_marker()
                # a robot may can collide with another in state done or in state star, 
                # but in this case motors stop
                move_on_edge()

                neighbors_states, blocked_last_move = get_node_info()
                nbr_done_robots = get_state_robots(neighbors_states, robot_state='done')

                begin_time = wait_clock(begin_time)

                # if found exactly one neighbor in state stopped or all the neighbors in state done
                if (len(neighbors_states) == 1 and neighbors_states[0] == 'stopped') or (nbr_done_robots > 0 and nbr_done_robots == len(neighbors_states)):

                    if neighbors_states[0] == 'stopped':
                        print('met a robot in state stopped')
                    else:
                        print('met ' + str(nbr_done_robots) + ' robots in state done')

                    # if nbr of done robots is odd
                    if nbr_done_robots % 2 == 1:
                        # note that this case never happen when the nbr of robots is 3
                        state = 'done'
                        # [TODO] try to think how more that two robots can exit the node
                    else:
                        # for simplicity we consider only the case of max 3 robots
                        # this means that robot reachs a marker while only one stopped robot is on the other side of the node
                        # meanwhile, a stopped robot, meeting a collect robot, became return

                        #motor_m.run_to_abs_pos(position_sp = 45)
                        cross_marker()
                        # rotate over node in order to reach other robot
                        # robot should stop due to collision avoidance setting
                        #rotate_over_node(collision_distance=collision_avoidance_distance)
                        rotate_over_node(time_out=3)
                        #motor_m.run_to_abs_pos(position_sp = 0)
                        # sync, during this time stopped robot waits
                        begin_time = wait_clock(begin_time)
                        # no need to check state
                        # complete node
                        rotate_over_node(time_to_settle=0)

                        first_returning_robot = False
                        state = 'return'

                        # notify the change of direction (turned = 1)
                        set_node_info(state, turned=1, stopped=1)

                elif blocked_last_move:
                    print('collect robot meets M')
                    cross_marker()
                    rotate_over_node()
                    state = 'return'

        elif state == 'return':

            neighbors_states, blocked_last_move = get_node_info()
            nbr_star_robots = get_state_robots(neighbors_states, robot_state = 'star')
            nbr_done_robots = get_state_robots(neighbors_states, robot_state = 'done')

            if nbr_star_robots == 1:
                print('met a robot in state star')
                # [TODO] solve following for this case

                if nbr_done_robots == 1:
                    state = 'gathering'
                    set_node_info(state, stopped=1)
            else:
                # no need to check if M is over next node
                set_node_info(state)

                # collection of more robots has been implemented by setting all these robots
                # in state return, before moving a robot check if it is not the first returning robot
                # ie it is not over a marker, it's over black line
                # (we assume that no more than 2 robots are returning)
                #if not is_not_color_black( [color.value()] ): # color must be in COL-REFLECT mode
                if not first_returning_robot: # color must be in COL-REFLECT mode
                    print('I\'m the second returning robot')
                    sleep(0.5)
                    # complete the edge
                    move_on_edge(collision_distance=-1, time_to_settle=0)

                cross_marker()
                robot_collision = move_on_edge()

                # sync
                neighbors_states, blocked_last_move = get_node_info()

                begin_time = wait_clock(begin_time)

                nbr_done_robots = get_state_robots(neighbors_states, robot_state = 'done')

                # returning robot perform gathering
                if nbr_done_robots >= 1:
                    # the first one move for some seconds, to leave some space for the incoming robot
                    if not robot_collision:
                        print('first returning robot performs gathering')
                        cross_marker()
                        move_on_edge(collision_distance=-1, time_out=2)
                    else:
                        print('second returning robot performs gathering')
                        # the second one move for at most 2 seconds, but is stops if it detects a collision
                        sleep(1.5)
                        move_on_edge(time_out=2)
                    # in both case, perform gathering
                    state = 'gathering'
                    set_node_info(state, stopped=1)

        elif state == 'done':
            # no need to set it
            neighbors_states, blocked_last_move = get_node_info()
            begin_time = wait_clock(begin_time)

            # no more than one robot reach a done robot
            if len(neighbors_states) >= 1 and neighbors_states[0] == 'return':
                print('met a robot in state return')
                # a stopped robot rotated over node, so direction is changed
                # new state is set in next state
                state = 'gathering'
                set_node_info(state, stopped=1)

        elif state == 'gathering':
            # protocol ends
            break


if __name__ == '__main__':
    main()
