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
    print('protocol begins')

    '''
    each clock follows these sequences of instruction:
        state = 'state name'
        set state function
        movement or rotation
        get states function
        sync clock function
    '''

    if us.connected:
        us.mode = 'US-DIST-CM'

    if ir.connected:
        ir.mode = 'IR-PROX'

    # move untill no other robot block M
    while not set_node_info_m():
        sleep(1)
        cross_marker()
        move_on_edge(collision_distance=-1)
        # no need to sync, M is asynchronous

if __name__ == '__main__':
    main()
