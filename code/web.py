#!/usr/bin/env python3

import time
import random
import socket
from flask import Flask, render_template, redirect, url_for, request, jsonify
import config

log = None

# classes

class Agent():
    def __init__(self, ip, cw=True, node=None, state='initial'):
        self.ip = ip
        self.cw = cw
        self.state = state
        self.node = node

    def __repr__(self):
        return 'Agent: ip {}, direction CW: {}, state: {}, node: {}'.format(self.ip, self.cw, self.state, self.node)

class Node():
    def __init__(self, label):
        assert isinstance(label, int), 'Node constructor accepts numeric label only' 
        self.label = label
        # list of agent ips in the current node
        self.agents = []

    def add_agent(self, agent_ip):
        # add an agent ip to the list of agents in the current node
        self.agents.append(agent_ip)

    def __repr__(self):
        return '<Node {}: [{}]>'.format(self.label, ' | '.join(str(app.agents[ip]) for ip in self.agents))


class Ring():
    def __init__(self, n_nodes):
        self._nodes = [Node(i) for i in range(n_nodes)]
        self.n_nodes = n_nodes

    def get_node(self, label):
        return self._nodes[label]

    def next(self, agent):
        """Return next node."""

        i = 1 if agent.cw else -1
        return self._nodes[(agent.node+i) % self.n_nodes]

    def prev(self, agent):
        """Return prev node."""

        i = -1 if agent.cw else 1
        return self._nodes[(agent.node+i) % self.n_nodes]

    def blocked(self, agent):
        """Check if the next node is blocked."""

        next_node = self.next(agent)
        if agent.ip == app.malicious_ip:
            return len(next_node.agents) > 0
        else:
            return app.malicious_ip in next_node.agents

    def random_place_agents(self):
        """Randomly place agents in the ring."""

        #a = app.agents[app.agents_ips[0]]
        #a.node = 1
        #self.get_node(1).add_agent(a.ip)
        #a.cw = False
        
        #a = app.agents[app.agents_ips[1]]
        #a.node = 2
        #self.get_node(2).add_agent(a.ip)
        #a.cw = False
        
        #a = app.agents[app.agents_ips[2]]
        #a.node = 4
        #self.get_node(4).add_agent(a.ip)
        #a.cw = True
        
        #a = app.agents[app.malicious_ip]
        #a.node = 6
        #self.get_node(6).add_agent(a.ip)
        #a.cw = True

        # True = clockwise
        # False = counterclockwise

        a = app.agents[app.agents_ips[0]]
        a.node = 3
        self.get_node(3).add_agent(a.ip)
        a.cw = False
        
        a = app.agents[app.agents_ips[1]]
        a.node = 6
        self.get_node(6).add_agent(a.ip)
        a.cw = False
        
        a = app.agents[app.agents_ips[2]]
        a.node = 5
        self.get_node(5).add_agent(a.ip)
        a.cw = True
        
        a = app.agents[app.malicious_ip]
        a.node = 1
        self.get_node(1).add_agent(a.ip)
        a.cw = False

        return
        
        # at most 1 agent per node, randomize direction in case of unoriented ring
        for agent, node in zip(app.agents.values(), random.sample(self._nodes, len(app.agents.keys()))):
            agent.cw = True if config.oriented else random.choice([True, False])
            agent.node = node.label
            self.get_node(node.label).add_agent(agent.ip)

    def dump(self):
        ring = dict()
        for node in self._nodes:
           ring[str(node.label)] = [(app.agents[a].ip, str(app.agents[a].cw), app.agents[a].state, app.agents[a].node) for a in node.agents]
        return ring

    def __repr__(self):
        return ', '.join(str(node) for node in self._nodes)


class MTFGRServer(Flask):
    '''Wrapper around the Flask class used to store additional information.'''

    def __init__(self, *args, **kwargs):
        super(MTFGRServer, self).__init__(*args, **kwargs)

        self.ring = Ring(config.n_nodes)
        self.agents_ips = config.agents_ips
        self.agents = dict()
        self.malicious_ip = config.malicious_ip
        self.oriented = config.oriented
        self.started = False


# instance of the web application

app = MTFGRServer(__name__)


# auxiliary functions

def _reset():
    """Reset the global variables by parsing again the config file."""
    import config
    global log

    app.ring = Ring(config.n_nodes)
    app.agents = {ip: Agent(ip) for ip in config.agents_ips}
    app.malicious_ip = config.malicious_ip
    app.agents[app.malicious_ip] = Agent(app.malicious_ip, state='malicious')
    app.oriented = config.oriented
    app.started = False
    app.ring.random_place_agents()
    
    log = open('/tmp/ev3.log', 'a')
    log.write('\n\nIIIIIIIIIINNNNNNNNNIIIIIIIIIIITTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTTT\\n\n')

# views

def _communicate_start():
    """Instruct each bot to start."""

    port = 31337
    for ip in app.agents_ips[::-1] + [app.malicious_ip]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        # s.sendall(b'Go!\n')
        s.close()

@app.route('/start')
def start():
    app.started = True
    try:
        _communicate_start()
    except Exception:
        pass
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    _reset()
    return redirect(url_for('index'))

@app.route('/status')
def global_status():
    """Get the whole ring status."""

    return jsonify(**app.ring.dump())

@app.route('/get/<agent_ip>')
def get_status(agent_ip):
    """Get the list of agents in the current node."""

    agent = app.agents[agent_ip]
    # aggiungere blocked
    return jsonify(agents=[app.agents[ip].state for ip in app.ring.get_node(agent.node).agents if ip != agent_ip],
                   blocked=app.ring.blocked(agent))

@app.route('/set/<agent_ip>', methods=['GET'])
def set_status(agent_ip):
    global log
    
    turned = request.args.get('turned') == '1' 
    state = request.args.get('state')
    stopped = request.args.get('stopped') == '1'
    
    # logging
    sss = '\n\n[Request] {} - ip: {}, turned: {}, state: {}, stopped: {}\n'.format(time.time(), agent_ip, turned, state, stopped)
    log.write(sss)
    log.write('[Status pre]\n')
    log.write(str(app.ring.dump()))
    
    
    agent = app.agents[agent_ip]
    agent.state = state
    agent.cw = agent.cw if not turned else not agent.cw

    blocked = app.ring.blocked(agent)
    if not blocked and not stopped:
        # advance to the next node if not blocked
        node = app.ring.get_node(agent.node)
        next_node = app.ring.next(agent)
        agent.node = next_node.label
        node.agents.remove(agent_ip)
        next_node.add_agent(agent_ip)

    log.write('\n[Status post]\n')
    log.write(str(app.ring.dump()))
    
    return jsonify(blocked=blocked)

@app.route('/')
def index():
    return render_template('base.html', started=app.started)

def main():
    app.run(host='0.0.0.0', debug=config.debug)

if __name__ == '__main__':
    main()
