#!/usr/bin/env python3

import random
from flask import Flask, render_template, redirect, url_for, request, jsonify
import config


# classes

class Agent():
    def __init__(self, ip, cw=True, node=None, state='INIT'):
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

        # TODO: could we use this function to check if the malicious user is allowed to go on?
        next_node = self.next(agent)
        return app.malicious_ip in next_node.agents

    def random_place_agents(self):
        """Randomly place agents in the ring."""

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

    app.ring = Ring(config.n_nodes)
    app.agents = {ip: Agent(ip) for ip in config.agents_ips}
    app.malicious_ip = config.malicious_ip
    app.agents[app.malicious_ip] = Agent(app.malicious_ip, state='MALICIOUS')
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
    turned = request.args.get('turned') == '1'
    state = request.args.get('state')

    agent = app.agents[agent_ip]
    agent.state = state
    agent.cw = agent.cw if not turned else not agent.cw

    blocked = app.ring.blocked(agent)
    if not blocked:
        # advance to the next node if not blocked
        node = app.ring.get_node(agent.node)
        next_node = app.ring.next(agent)
        agent.node = next_node.label
        node.agents.remove(agent_ip)
        next_node.add_agent(agent_ip)

    return jsonify(blocked=blocked)

@app.route('/')
def index():
    return render_template('base.html', started=app.started)

def main():
    app.run(debug=config.debug)

if __name__ == '__main__':
    main()