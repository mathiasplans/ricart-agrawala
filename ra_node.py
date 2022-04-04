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
    other_id = -1

    def __init__(self, p):
        self.p = p
        pass

    def exposed_info(self, id, lamport):
        self.other_lamport = lamport
        self.other_id = id
        self.p.max_time(self.other_lamport)

    def exposed_get_lamport(self):
        return self.p.get_time()

    def exposed_ask_cs(self):
        while True:
            if self.p.state == "DO-NOT-WANT":
                return

            elif self.p.state == "HELD":
                pass

            elif self.p.state == "WANTED":
                self_is_greater_id = self.p.id > self.other_id
                self_ts_is_greater = self.p.wanted_ts > self.other_lamport
                ts_is_equal = self.p.wanted_ts == self.other_lamport
                if self_ts_is_greater or (ts_is_equal and not self_is_greater_id):
                    return

            time.sleep(0.2)

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
        with self.lock:
            self.lamport += 1
            return self.lamport

    def max_time(self, other):
        with self.lock:
            self.lamport += 1
            self.lamport = max(self.lamport, other)
            return self.lamport

    def get_time(self):
        with self.lock:
            return self.lamport

    def get_state(self):
        return self.state

    def rpyc_start(self):
        self.ts.start()

    def start(self):
        _thread.start_new_thread(self.rpyc_start, ())
        _thread.start_new_thread(self.run, ())

    def get_cs(self):
        self.wanted_ts = self.increment_time()

        # Ask permission from others
        # if this loop terminates then all the permissions were given
        for p in others:
            c = rpyc.connect("localhost", p)
            c._config['sync_request_timeout'] = None # Turn of the timeout
            c.root.info(self.id, self.wanted_ts)
            c.root.ask_cs()

    def run(self):
        # with 5 second interval, update clock
        while True:
            if self.state == "HELD":
                time.sleep(10)
                self.lamport += 1
                self.state = "DO-NOT-WANT"

            elif self.state == "WANTED":
                self.get_cs()
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

        cmd = command_string.split(" ")

        command = cmd[0]

        # handle exit
        if command == "Exit":
            running = False

        # handle list
        elif command == "List":
            try:
                for p in processes:
                    print(f"P{p.id}, {p.state}")
            except:
                print("Error")
