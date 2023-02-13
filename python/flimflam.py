#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from plano import *

class Runner:
    def __init__(self, kwargs):
        self.relay = relays[kwargs["relay"]]
        self.workload = workloads[kwargs["workload"]]
        self.jobs = kwargs["jobs"]
        self.warmup = kwargs["warmup"]
        self.duration = kwargs["duration"]

        self.output_dir = make_temp_dir()

    def run(self, capture):
        assert capture is not None

        self.relay.check()
        self.workload.check()

        procs = list()

        connect_port = 20001
        listen_port = 20002

        if self.relay is relays["none"]:
            connect_port = listen_port
        else:
            procs.append(self.relay.start_relay_1(self))
            procs.append(self.relay.start_relay_2(self))

        try:
            procs.append(self.workload.start_server(self, listen_port))

            await_port(listen_port)
            await_port(connect_port)

            procs.append(self.workload.start_client(self, connect_port))

            pids = [str(x.pid) for x in procs]

            with start(f"pidstat 2 --human -l -t -p {','.join(pids)}"):
                sleep(self.warmup)

                if self.relay is relays["none"]:
                    sleep(self.duration)
                else:
                    with ProcessMonitor(pids[0]) as mon1, ProcessMonitor(pids[1]) as mon2:
                        capture(pids[0], pids[1], self.duration)

                sleep(1) # So the workload can self-terminate
        finally:
            for proc in procs:
                kill(proc)

            for proc in procs:
                wait(proc)

        results = self.workload.process_output(self)

        summary = {
            "configuration": {
                "relay": self.relay.name,
                "workload": self.workload.name,
                "jobs": self.jobs,
                "warmup": self.warmup,
                "duration": self.duration,
                "output_dir": self.output_dir,
            },
            "results": results,
        }

        if self.relay is not relays["none"]:
            summary["resources"] = {
                "relay_1": {
                    "average_cpu": mon1.get_cpu(),
                    "max_rss": mon1.get_rss(),
                },
                "relay_2": {
                    "average_cpu": mon2.get_cpu(),
                    "max_rss": mon2.get_rss(),
                },
            }

        write_json(join(self.output_dir, "summary.json"), summary)

        return self.output_dir

    def print_summary(self):
        data = read_json(join(self.output_dir, "summary.json"))

        print_heading("Configuration")

        config = data["configuration"]

        props = [
            ["Relay", config["relay"]],
            ["Workload", config["workload"]],
            ["Jobs", config["jobs"]],
            ["Warmup", format_duration(config["warmup"])],
            ["Duration", format_duration(config["duration"])],
            ["Output dir", config["output_dir"]],
        ]

        print_properties(props)

        print_heading("Results")

        results = data["results"]

        props = [
            ["Duration", format_duration(results["duration"])],
        ]

        if "octets" in results:
            props += [
                ["Octets", format_quantity(results["octets"])],
                ["Bits/s", format_quantity(results["octets"] * 8 / results["duration"])],
            ]

        if "operations" in results:
            props += [
                ["Operations", format_quantity(results["operations"])],
                ["Operations/s", format_quantity(results["operations"] / results["duration"])],
            ]

        print_properties(props)

        if "resources" in data:
            print_heading("Resources")

            resources = data["resources"]

            props = [
                ["Relay 1 average CPU", format_percent(resources["relay_1"]["average_cpu"])],
                ["Relay 1 max RSS", format_quantity(resources["relay_1"]["max_rss"], mode="binary")],
                ["Relay 2 average CPU", format_percent(resources["relay_2"]["average_cpu"])],
                ["Relay 2 max RSS", format_quantity(resources["relay_2"]["max_rss"], mode="binary")],
            ]

            print_properties(props)

import os as _os
import resource as _resource
import threading as _threading
import time as _time

_ticks_per_ms = _os.sysconf(_os.sysconf_names["SC_CLK_TCK"]) / 1000
_page_size = _resource.getpagesize()

class ProcessMonitor(_threading.Thread):
    def __init__(self, pid):
        super().__init__()

        self.pid = pid
        self.stopping = _threading.Event()
        self.samples = list()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.join()

    def read_cpu_and_rss(self):
        proc_file = _os.path.join("/", "proc", str(self.pid), "stat")

        with open(proc_file) as f:
            line = f.read()

        fields = line.split()

        time = _time.time()
        cpu = int(sum(map(int, fields[13:17])) / _ticks_per_ms)
        rss = int(fields[23]) * _page_size

        return time, cpu, rss

    def run(self):
        prev_time, prev_cpu, _ = self.read_cpu_and_rss()

        while not self.stopping.wait(1):
            curr_time, curr_cpu, rss = self.read_cpu_and_rss()

            period_cpu = curr_cpu - prev_cpu
            prev_cpu = curr_cpu

            period_time = curr_time - prev_time
            prev_time = curr_time

            cpu = period_cpu / (period_time * 1000)

            self.samples.append((cpu, rss))

    def stop(self):
        self.stopping.set()

    def get_cpu(self):
        if not self.samples:
            return 0

        return sum([x[0] for x in self.samples]) / len(self.samples)

    def get_rss(self):
        if not self.samples:
            return 0

        return max([x[1] for x in self.samples])

class Workload:
    def __init__(self, name):
        self.name = name

class Builtin(Workload):
    def check(self):
        check_exists("client")
        check_exists("server")

    def start_client(self, runner, port):
        return start(f"./client {port} {runner.jobs} {runner.output_dir}")

    def start_server(self, runner, port):
        return start(f"./server {port}")

    def process_output(self, runner):
        total = 0

        for i in range(runner.jobs):
            line = tail(f"{runner.output_dir}/transfers.{i}.csv", 1)
            values = line.split(",", 1)

            try:
                total += int(values[1])
            except IndexError:
                print("ERROR: Unexpected transfer value:", values)

        # XXX This is currently warmup + duration because I haven't
        # worked out how to isolate the transfer data for the duration
        # period only.
        summary = {
            "octets": total,
            "duration": runner.warmup + runner.duration,
        }

        return summary

class Iperf3(Workload):
    def check(self):
        check_program("iperf3", "I can't find iperf3.  Run 'dnf install iperf3'.")

    def start_client(self, runner, port):
        return start(f"iperf3 --client 127.0.0.1 --port {port} --parallel {runner.jobs}"
                     f" --json --logfile {runner.output_dir}/output.json --time 86400 --omit {runner.warmup}")

    def start_server(self, runner, port):
        return start(f"iperf3 --server --port {port}")

    def process_output(self, runner):
        output = read_json(join(runner.output_dir, "output.json"))

        summary = {
            "octets": output["end"]["sum_sent"]["bytes"],
            "duration": output["end"]["sum_sent"]["seconds"],
        }

        return summary

class H2load(Workload):
    def check(self):
        check_program("h2load", "I can't find h2load.  Run 'dnf install nghttp2'.")
        check_program("nginx", "I can't find nginx.  Run 'dnf install nginx'.")

    def start_client(self, runner, port):
        return start(f"h2load --h1 --warm-up-time {runner.warmup} --duration {runner.duration}"
                     f" --clients {runner.jobs} --threads {runner.jobs}"
                     f" http://localhost:{port}/index.txt",
                     stdout=join(runner.output_dir, "output.txt"))

    def start_server(self, runner, port):
        write("/tmp/flimflam/http-server/web/index.txt", "x" * 100)
        return start(f"nginx -c $PWD/config/http-server.conf -e /dev/stderr")

    def process_output(self, runner):
        output = read_lines(join(runner.output_dir, "output.txt"))

        for line in output:
            if line.startswith("requests:"):
                operations = int(line.split()[1])
                break
        else:
            raise Exception(output)

        for line in output:
            if line.startswith("traffic:"):
                octets = int(line.split()[2][1:-1])
                break
        else:
            raise Exception(output)

        data = {
            "octets": octets,
            "operations": operations,
            "duration": runner.duration,
        }

        return data

class Relay:
    def __init__(self, name):
        self.name = name

    def check(self):
        pass

class Skrouterd(Relay):
    def check(self):
        check_program("taskset", "I can't find taskset.  Run 'dnf install util-linux-core'.")
        check_program("skrouterd", "I can't find skrouterd.  Make sure it's on the path.")

    def start_relay_1(self, runner):
        return start(f"taskset --cpu-list 0 skrouterd --config $PWD/config/skrouterd1.conf")

    def start_relay_2(self, runner):
        return start(f"taskset --cpu-list 2 skrouterd --config $PWD/config/skrouterd2.conf")

class Nginx(Relay):
    def check(self):
        check_program("taskset", "I can't find taskset.  Run 'dnf install util-linux-core'.")
        check_program("nginx", "I can't find nginx.  Run 'dnf install nginx'.")

        if not exists("/usr/lib64/nginx/modules/ngx_stream_module.so"):
            exit("To use Nginx as a relay, I need the stream module.  "
                 "Run 'dnf install nginx-mod-stream'.")

    def start_relay_1(self, runner):
        return start(f"taskset --cpu-list 0 nginx -c $PWD/config/nginx1.conf -e /dev/stderr")

    def start_relay_2(self, runner):
        return start(f"taskset --cpu-list 2 nginx -c $PWD/config/nginx2.conf -e /dev/stderr")

# sockperf under-load -i 127.0.0.1 -p 5001 --tcp
# sockperf server -i 127.0.0.1 -p 5001 --tcp

relays = {
    "skrouterd": Skrouterd("skrouterd"),
    "nginx": Nginx("nginx"),
    "none": Relay("none"),
}

workloads = {
    "builtin": Builtin("builtin"),
    "iperf3": Iperf3("iperf3"),
    "h2load": H2load("h2load"),
}

def print_heading(name):
    print()
    print(name.upper())
    print()

from dataclasses import dataclass as _dataclass

def print_table(data, align=None):
    column_count = 0

    for row in data:
        column_count = max(column_count, len(row))

    @_dataclass
    class Column:
        width: int
        align: str

    if align is None:
        align = "l"

    assert len(align) > 0

    if len(align) < column_count:
        align += align[-1] * (column_count - len(align))

    columns = [Column(0, align[i]) for i in range(column_count)]
    placeholder = "-"
    padding = 3

    for row in data:
        for j, column in enumerate(columns):
            try:
                datum = row[j]
            except IndexError:
                datum = placeholder

            column.width = max(column.width, len(str(datum)))

    for i, row in enumerate(data):
        for j, column in enumerate(columns):
            try:
                datum = row[j]
            except IndexError:
                datum = placeholder

            if datum is None:
                datum = placeholder

            if column.align == "l":
                print(str(datum).ljust(column.width), end="")
            else:
                print(str(datum).rjust(column.width), end="")

            if j < len(columns) - 1:
                print(" " * padding, end="")

        print()

        if i == 0:
            for j, column in enumerate(columns):
                print("-" * column.width, end="")

                if j < len(columns) - 1:
                    print("-" * padding, end="")

            print()

def format_quantity(number, mode="decimal"):
    if mode == "decimal":
        tiers = (
            (10**9, "G"),
            (10**6, "M"),
            (10**3, "K"),
        )
    elif mode == "binary":
        tiers = (
            (2**30, "G"),
            (2**20, "M"),
            (2**10, "K"),
        )
    else:
        raise Exception("Unknown mode argument")

    for tier in tiers:
        if number / tier[0] >= 1:
            return "{:,.1f}{}".format(number / tier[0], tier[1])

    return "{:,.1f}".format(number)

def format_percent(number):
    return "{:,.0f}%".format(number * 100)