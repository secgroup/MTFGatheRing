#from rvor_functions import move_on_edge, rotate_over_node
from robot_functions import *
from requests import post
from json import loads

def main():
    # query the server to start
    print('connect to server')

    start()


    # after that each robot uses an own counter
    # in this way all the robot operations are synchronized
    begin_time = int(time())
    print('protocol begins')

    # !!! make sure robot eyes are looking at left
    # if not, protocol does not work as expected
    init_eyes_motor(eyes_speed)

    # init values
    #moved = False
    #clockwise_direction = True
    state = 'initial'
    special_node_reached = 0
    turned = False

    print('\t' + 'state: ' + str(state).upper())

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    previous_state = state

    while True:
        # print current state for debugging
        if (previous_state != state):
            print('\t' + 'state: ' + str(state).upper())
            previous_state = state

        
        if state == 'initial':

            # notify to server the intention of moving
            blocked_last_move = set_node_info(turned, state)

            # [TODO]
            # add this condition in protocol, an agent can be blocked before moving
            if blocked_last_move:
                print('robot is blocked in last move')
                state = 'stopped'
                # move robot on the other side of the node
                turned = True
                set_node_info(turned, state, stopped = 1)
                cross_marker()
                rotate_over_node()
                begin_time = wait_clock(begin_time)

            else: # robot moves
                cross_marker()
                # a robot may can collide with another in state done, but in this case motors stop
                move_on_edge()
                # after that robot moved, it syncronize its clock waiting the remaining time
                begin_time = wait_clock(begin_time)

                # then it "looks around" to collect the states of the other robots on the same node
                # actually, these states have been stored before, with the call of set_node_info function performed by each robot
                neighbors_states, blocked_last_move = get_node_info()
            
                # no more than one robot for a node can be in state stopped
                if len(neighbors_states) == 1 and neighbors_states[0] == 'stopped':
                    print('met a robot in state stopped')
                    state = 'done'
                    # move robot on the other side of the node, take the place of stopped robot
                    cross_marker()
                    rotate_over_node()
                    turned = True

                    set_node_info(turned, state, stopped = 1)

                    begin_time = wait_clock(begin_time)

                # [TODO] no more valid condition, wait for new protocol
                # no more than one robot for a node can be in state star
                elif len(neighbors_states) == 1 and neighbors_states[0] == 'star':
                    print('met a robot in state star')
                    state = 'check'

                # no more than one robot in state initial can reach M,
                # without first reach a stopped robot
                elif len(neighbors_states) == 0 and blocked_last_move:
                    state = 'stopped'
                    # move robot on the other side of the node
                    # because no other robots could come from the opposite direction,
                    # since M block them
                    cross_marker()
                    rotate_over_node()
                    turned = True

                    set_node_info(turned, state, stopped = 1)

                    begin_time = wait_clock(begin_time)

                elif is_special_node():
                    special_node_reached += 1
                    if special_node_reached == 2:
                        state = 'star'
                        # move robot in the middle of the curve
                        # because other robots could arrive from both the direction
                        # but when they arrived from the same direction, they must go straight on
                        cross_marker()
                        # [TODO]
                        # unfortunately node is small, the exact time to rotate is important
                        # to avoid robots to bump one to each other
                        rotate_over_node(time_out=4.5)

        # [TODO] add this part is protocol? The semantic is the same
        elif state == 'stopped':
            turned = False

            neighbors_states, blocked_last_move = get_node_info()

            # no more than one robot reach a stopped robot
            if len(neighbors_states) == 1 and neighbors_states[0] == 'initial':
                print('met a robot in state initial')
                # a stopped robot rotated over node, so direction is changed
                # new state is set in next state
                state = 'collect'

            elif len(neighbors_states) == 1 and neighbors_states[0] == 'collect':
                print('met a robot in state collect')
                # a stopped robot rotated over node, so direction is changed
                # new state is set in next state
                state = 'return'
            '''
            elif len(neighbors_states) == 1 and neighbors_states[0] == 'check':
                print('met a robot in state check')
                # a stopped robot rotated over node, so direction is changed
                #turned = True
                state = 'return'
            '''
            # wait only if the state remain stopped, otherwise start moving, see others state
            else:
                begin_time = wait_clock(begin_time)

        elif state == 'collect':
            # notify to server the intention of moving
            blocked_last_move = set_node_info(turned, state)
            # turned variable is setted to True by previous state
            # for next clock it's True because robot has already turned
            turned = False

            # [TODO]
            # add this condition in protocol, if there is only one stopped robot
            # collect agent will be bump against M, if first it moves then it checks
            if blocked_last_move:
                print('robot is blocked in last move')
                state = 'return'
                # move robot on the other side of the node
                cross_marker()
                rotate_over_node()

            else: # robot moves
                cross_marker()
                # a robot may can collide with another in state done or in state star, 
                # but in this case motors stop
                move_on_edge()
                begin_time = wait_clock(begin_time)

                neighbors_states, blocked_last_move = get_node_info()
            
                nbr_done_robots, done_neighbors = get_done_robots(neighbors_states)

                # no more than one robot for a node can be in state star
                if len(neighbors_states) == 1 and neighbors_states[0] == 'star':
                    print('met a robot in state star')
                    state = 'check'
                    # [TODO]
                    # add change direction in protocol?
                    cross_marker()
                    rotate_over_node()

                # if found exactly one neighbor in state stopped or all the neighbors in state done
                elif (len(neighbors_states) == 1 and neighbors_states[0] == 'stopped') or (nbr_done_robots == len(neighbors_states)):
                    if neighbors_states[0] == 'stopped':
                        print('met a robot in state stopped')
                    else:
                        print('met ' + str(nbr_done_robots) + ' robots in state done')

                    # if nbr of done robots is odd
                    if nbr_done_robots % 2 == 1:
                        # note that this case never happen when the nbr of robots is 3
                        state = 'done'
                    else:
                        # for simplicity we consider only the case of max 3 robots
                        # this means that robot reach a marker while a stopped robot is on the other side of the node
                        # [TODO] try to think how more that two robots can exit the node
                        # meanwhile, a stopped robot, meeting a returning robot, became return
                        cross_marker()
                        rotate_over_node()
                        state = 'return'
                        turned = True

                        set_node_info(turned, state, stopped = 1)

                        begin_time = wait_clock(begin_time)

                elif blocked_last_move:
                    print('collect robot meets M')
                    cross_marker()
                    rotate_over_node()
                    state = 'return'
                    turned = True


        # [TODO] manage collision between two returning robot!!!
        elif state == 'return':
            # robot can not meet M, so move without check it
            set_node_info(turned, state)
            turned = False
            # a robot may can collide with another one
            # but in this case motors stop
            robot_collision = move_on_edge()
            neighbors_states, blocked_last_move = get_node_info()

            nbr_done_robots, done_neighbors = get_done_robots(neighbors_states)

            # a return robot must meet at least one robot in state done
            if nbr_done_robots >= 1:
                print('met ' + str(nbr_done_robots) + ' robots in state done')
                # [TODO] add this final state also in protocol
                state = 'gathering'
            else:
                # after moving, synchronise with the clock
                begin_time = wait_clock(begin_time)

        elif state == 'check':
            pass            

        elif state == 'done':
            print('[TODO] implement it')
            sleep(2)

        elif state == 'gathering':
            # protocol ends
            break


if __name__ == '__main__':
    main()
