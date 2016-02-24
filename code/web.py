#!/usr/bin/env python3

from flask import Flask, render_template, redirect, url_for
import config

class Node():
    def __init__(self, label):
        assert isinstance(label, int), 'Numeric labels only' 
        self.label = label

    def __repr__(self):
        return '<- {} ->'.format(self.label)

class Ring():
    def __init__(self, n_nodes):
        print([Node(i) for i in range(n_nodes)])
        self.nodes = [Node(i) for i in range(n_nodes)]
        self.n_nodes = n_nodes

    def next(self, node):
        """Return next node in CW order."""

        return self.nodes[(node.label+1) % self.n_nodes]

    def prev(self, node):
        """Return prev node in CW order."""

        return self.nodes[(node.label-1) % self.n_nodes]

    def __repr__(self):
        return ', '.join(str(node) for node in self.nodes)

class MTFGRServer(Flask):
    '''Wrapper around the Flask class used to store additional information.'''

    def __init__(self, *args, **kwargs):
        super(MTFGRServer, self).__init__(*args, **kwargs)

        self.ring = Ring(config.n_nodes)
        self.agents = config.agents
        self.started = False

# instance of the web application
app = MTFGRServer(__name__)

@app.route('/started')
def started():
    """Page polled by the bots to start the protocol."""

    return '1' if app.started else '0'

@app.route('/start')
def start():
    app.started = True
    return redirect(url_for('index'))

@app.route('/')
def index():
    return render_template('base.html', started=app.started)

def main():
    app.run(debug=True)

if __name__ == '__main__':
    main()