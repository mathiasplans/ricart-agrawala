import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.utils.helpers import classpartial
import datetime
import time
from functools import wraps
import random
import sys
import _thread
import asyncio

N = int(sys.argv[1])
others = []

p_upper = 5
cs_upper = 10

def parallel(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped

def CS():
    time.sleep(random.uniform(10, cs_upper))

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

    # Ask for permission to use CS
    # returning means giving permission
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

                # Conflicts are resolved by prioritizing higher ID processes
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
        self.lock = _thread.allocate_lock()
        self.loop = None

        partialserv = classpartial(Serv, self);
        self.ts = ThreadedServer(partialserv, port=port)

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

        # This has to be done in parallel because
        # otherwise higher ID tasks get the resource
        # more often than lower ID tasks. Basically
        # some tasks will block this so higher ID
        # tasks will not get polled, so the timestamp
        # is not propagated and the asking timestamp
        # will be therefore lower usually.
        #
        # This is fixed with doing it in parallel.
        @parallel
        def ask_permission(p):
            c = rpyc.connect("localhost", p)
            c._config['sync_request_timeout'] = None # Turn off the timeout
            c.root.info(self.id, self.wanted_ts)
            c.root.ask_cs()
            c.close()

        # Ask permission from others
        awaitables = []
        for p in others:
            if p == self.port:
                continue

            awaitables.append(ask_permission(p))

        # if this loop terminates then all the permissions were given
        self.loop.run_until_complete(asyncio.gather(*awaitables))

    def run(self):
        # Create an event loop for this thread
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Add a random delay at the beginning
        # for added realism
        time.sleep(random.uniform(1.5, 6.5))

        # with 5 second interval, update clock
        while True:
            if self.state == "HELD":
                CS()
                self.increment_time()
                self.state = "DO-NOT-WANT"

            elif self.state == "WANTED":
                self.get_cs()
                self.state = "HELD"
                pass

            elif self.state == "DO-NOT-WANT":
                time.sleep(random.uniform(5, p_upper))
                self.increment_time()
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

        if command == "Exit":
            running = False

        elif command == "time-cs":
            newupper = int(cmd[1])
            if newupper >= 10:
                cs_upper = newupper

        elif command == "time-p":
            newupper = int(cmd[1])
            if newupper >= 5:
                p_upper = newupper

        elif command == "List":
            try:
                for p in processes:
                    debug = f"[{p.lamport}, {p.wanted_ts}]" if True else ""
                    print(f"P{p.id}{debug}, {p.state}")
            except:
                print("Error")
