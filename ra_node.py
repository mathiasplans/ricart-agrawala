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
others = []

class Serv(rpyc.Service):
    other_lamport = 0

    def __init__(self, p):
        self.p = p
        pass

    def exposed_get_lamport(self):
        return self.p.get_time()

    def exposed_ask_cs(self):
        while True:
            if self.p.state == "DO-NOT-WANT":
                return

            elif self.p.state == "HELD":
                pass

            elif self.p.state == "WANTED":
                if self.p.get_time() > self.other_lamport:
                    return

            time.sleep(0.2)

    def on_connect(self, conn):
        # Time management
        self.other_lamport = conn.root.get_lamport()
        self.p.max_time(self.other_lamport)


class Process:
    def __init__(self, id, port):
        self.id = id
        self.port = port
        self.lamport = 0
        self.state = "DO-NOT-WANT"
        self.wanted_ts = 0

        partialserv = classpartial(Serv, self);
        self.ts = ThreadedServer(partialserv, port=port)

        self.lock = _thread.allocate_lock()

    def increment_time(self):
        with lock:
            self.lamport += 1
            return self.lamport

    def max_time(self, other):
        with lock:
            self.lamport += 1
            self.lamport = max(self.lamport, other)
            return self.lamport

    def get_time(self):
        with lock:
            return self.lamport

    def get_state(self):
        return self.state

    def start(self):
        _thread.start_new_thread(self.run, ())

    def get_cs(self):
        self.wanted_ts = self.get_time()

        # Ask permission from others
        # if this loop terminates then all the permissions were given
        for p in others:
            self.increment_time()
            rpyc.connect("localhost", p)
            p.root.ask_cs()

    def run(self):
        # with 5 second interval, update clock
        while True:
            if self.state == "HELD":
                time.sleep(10)
                self.lamport += 1
                self.state = "DO-NOT-WANT"

            elif self.state == "WANTED":
                try_cs()
                self.state = "HELD"
                pass

            elif self.state == "DO-NOT-WANT":
                time.sleep(5)
                self.lamport += 1
                self.state = "WANTED"


if __name__=='__main__':
    id = 1
    port = 18812
    processes = []
    for i in range(N):
        p = Process(id, port)
        processes.append(p)
        others.append(port)

        port += 1
        id += 1

    for i in range(N):
        processes[i].start()

    running = True
    while running:
        command_string = input()

        inp = command_string.lower()
        cmd = inp.split(" ")

        command = cmd[0]

        # handle exit
        elif command == "Exit":
            running = False

        # handle list
        elif command == "List":
            try:
                self.list()
            except:
                print("Error")
