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

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    while True:
        print('try to move in one direction')
        blocked_last_move = set_node_info_m()

        if not blocked_last_move:
            cross_marker()
            move_on_edge()
            begin_time = wait_clock(begin_time) 

        else:
            print('M can not move\nrotate, if previous node is free')
            blocked_last_move = set_node_info_m(turned=1)
            if not blocked_last_move:
                cross_marker()
                rotate_over_node()
                begin_time = wait_clock(begin_time) 

            else:
                print('M is blocked in both the direction\nwait a while')
                sleep(3)

if __name__ == '__main__':
    main()
