import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.utils.helpers import classpartial
import datetime
import time
from functools import wraps
import random
import sys
import _thread

N = int(sys.argv[1])

HELD = 0
WANTED = 1
DO_NOT_WANT = 2
others = []

class Serv(rpyc.Service):
    def __init__(self, p):
        self.p = p
        pass

    def exposed_get_lamport(self):
        return self.p.lamport

    def on_connect(self, conn):
        # Time management
        other_lamport = conn.root.get_lamport()
        self.p.lamport = max(self.p.lamport + 1, other_lamport)

class Process:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.lamport = 0
        self.state = DO_NOT_WANT

        #partialserv = classpartial(Serv, self);
        #self.ts = ThreadedServer(partialserv, port=port)

    def start(self):
        _thread.start_new_thread(self.run, ())

    def run(self):
        # with 5 second interval, update clock
        while True:
            print("Tick")
            time.sleep(5)


if __name__=='__main__':
    id = 1
    port = 18812
    processes = []
    for i in range(N):
        p = Process(id, port)
        processes.append(p)

        others.append(port)
        port += 1

    for i in range(N):
        processes[i].start()

    # Let the threads do their work
    while True:
        pass
