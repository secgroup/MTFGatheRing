#!/usr/bin/env python3

import random
from enum import Enum
from flask import Flask, render_template, redirect, url_for, jsonify
import config


Direction = Enum('Direction', 'CW CCW')

# classes

class Agent():
    def __init__(self, ip, direction=None, node=None):
        self.ip = ip
        self.direction = direction
        self.node = node

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
        return '<- {}: [{}] ->'.format(self.label, ', '.join(self.agents))


class Ring():
    def __init__(self, n_nodes):
        self._nodes = [Node(i) for i in range(n_nodes)]
        self.n_nodes = n_nodes

    def get_node(self, label):
        return self._nodes[label]

    def next(self, agent):
        """Return next node."""

        i = 1 if agent.direction is Direction.CW else -1
        return self._nodes[(agent.node+i) % self.n_nodes]

    def prev(self, agent):
        """Return prev node."""

        i = 1 if agent.direction is Direction.CCW else -1
        return self._nodes[(agent.node-i) % self.n_nodes]

    def blocked(self, agent):
        """Check if the next node is blocked."""

        # TODO: could we use this function to check if the malicious user is allowed to go on?
        next_node = self.next(agent)
        if app.malicious_ip in next_node.agents:
            return True
        return False

    def random_place_agents(self):
        """Randomly place agents in the ring."""

        # at most 1 agent per node, randomize direction in case of unoriented ring
        for agent, node in zip(app.agents.values(), random.sample(self._nodes, len(app.agents.keys()))):
            agent.direction = Direction.CW if config.oriented else random.choice(list(Direction))
            agent.node = node.label
            self.get_node(node.label).add_agent(agent.ip)

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

    app.ring = Ring(config.n_nodes)
    app.agents = {ip: Agent(ip) for ip in config.agents_ips}
    app.malicious_ip = config.malicious_ip
    app.oriented = config.oriented
    app.started = False
    app.ring.random_place_agents()


# views

@app.route('/started')
def started():
    """Page polled by the bots to start the protocol."""

    return '1' if app.started else '0'

@app.route('/start')
def start():
    app.started = True
    return redirect(url_for('index'))

@app.route('/reset')
def reset():
    _reset()
    return redirect(url_for('index'))

@app.route('/get/<agent_ip>')
def get_status(agent_ip):
    """Get the list of agents in the current node and wether or not the next node is blocked."""

    agent = app.agents[agent_ip]
    return jsonify(agents=app.ring.get_node(agent.node).agents,
                   blocked=app.ring.blocked(agent))

@app.route('/set/<agent_id>/<turned>')
def set_status():
    return render_template('base.html', started=app.started)

@app.route('/')
def index():
    return render_template('base.html', started=app.started)

def main():
    app.run(debug=config.debug)

if __name__ == '__main__':
    main()