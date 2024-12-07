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
        self.relay = RELAYS[kwargs["relay"]]
        self.workload = WORKLOADS[kwargs["workload"]]
        self.protocol = kwargs["protocol"]
        self.jobs = kwargs["jobs"]
        self.warmup = kwargs["warmup"]
        self.duration = kwargs["duration"]
        self.cpu_limit = kwargs["cpu_limit"]
        self.call_graph = kwargs.get("call_graph")

        self.output_dir = make_temp_dir()

    def run(self, capture):
        self.relay.check(self)
        self.workload.check(self)

        check_program("pidstat", "I can't find pidstat.  Run 'dnf install sysstat'.")

        connect_port = 20001
        listen_port = 20002

        if self.relay is RELAYS["none"]:
            try:
                connect_port = listen_port

                self.workload.start_server(self, listen_port)

                await_port(listen_port)

                # Awkward sleep
                sleep(0.2)

                self.workload.start_client(self, connect_port)

                procs = [self.workload.client_proc, self.workload.server_proc]
                pids = [str(x.pid) for x in procs]

                with start(f"pidstat 2 --human -l -t -p {','.join(pids)}"):
                    sleep(self.warmup + self.duration)
            finally:
                self.workload.stop_client(self)
                self.workload.stop_server(self)
        else:
            assert capture is not None

            try:
                self.relay.start_relay_1(self)
                self.relay.start_relay_2(self)

                self.workload.start_server(self, listen_port)

                await_port(listen_port)
                await_port(connect_port)

                # Awkward sleep
                sleep(0.2)

                self.workload.start_client(self, connect_port)

                procs = [self.relay.relay_1_proc, self.relay.relay_2_proc,
                         self.workload.client_proc, self.workload.server_proc]
                pids = [str(x.pid) for x in procs]

                with start(f"pidstat 2 --human -l -t -p {','.join(pids)}"):
                    sleep(self.warmup)

                    with ProcessMonitor(pids[0]) as mon1, ProcessMonitor(pids[1]) as mon2:
                        capture(pids[0], pids[1], self.duration, self.call_graph)
            finally:
                self.workload.stop_client(self)
                self.workload.stop_server(self)
                self.relay.stop_relay_1(self)
                self.relay.stop_relay_2(self)

        results = self.workload.process_output(self)

        summary = {
            "configuration": {
                "workload": self.workload.name,
                "relay": self.relay.name,
                "protocol": self.protocol,
                "jobs": self.jobs,
                "warmup": self.warmup,
                "duration": self.duration,
                "cpu_limit": self.cpu_limit,
                "output_dir": self.output_dir,
            },
            "results": results,
        }

        if self.relay is not RELAYS["none"]:
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
            ["Workload", config["workload"]],
            ["Relay", config["relay"]],
            ["Protocol", config["protocol"]],
            ["Jobs", config["jobs"]],
            ["Warmup", format_duration(config["warmup"])],
            ["Duration", format_duration(config["duration"])],
            ["CPU limit", config["cpu_limit"]],
            ["Output dir", config["output_dir"]],
        ]

        print_properties(props)

        print_heading("Results")

        results = data["results"]

        props = [
            ["Duration", format_duration(results["duration"])],
        ]

        if "bits" in results:
            props += [
                ["Bits", format_quantity(results["bits"])],
                ["Bits/s", format_quantity(results["bits"] / results["duration"])],
            ]

        if "cnxs" in results:
            props += [
                ["Cnxs", format_quantity(results["cnxs"])],
                ["Cnxs/s", format_quantity(results["cnxs"] / results["duration"])],
            ]

        if "operations" in results:
            props += [
                ["Operations", format_quantity(results["operations"])],
                ["Operations/s", format_quantity(results["operations"] / results["duration"])],
            ]

        if "latency" in results:
            props += [
                ["Latency*", results["latency"]["average"]],
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
    def __init__(self, name, protocols):
        self.name = name
        self.protocols = protocols

        self.client_proc = None
        self.server_proc = None

    def stop_client(self, runner):
        if self.client_proc is not None:
            kill(self.client_proc)
            wait(self.client_proc)

    def stop_server(self, runner):
        if self.server_proc is not None:
            kill(self.server_proc)
            wait(self.server_proc)

class Builtin(Workload):
    def check(self, runner=None):
        if runner is not None:
            check_exists("$FLIMFLAM_HOME/builtin/client")
            check_exists("$FLIMFLAM_HOME/builtin/server")

    def start_client(self, runner, port):
        self.client_proc = start(f"$FLIMFLAM_HOME/builtin/client {port} {runner.jobs} {runner.output_dir}")

    def start_server(self, runner, port):
        self.server_proc = start(f"$FLIMFLAM_HOME/builtin/server {port}")

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
            "duration": runner.warmup + runner.duration,
            "bits": total * 8,
        }

        return summary

class ConnectionRate(Workload):
    def check(self, runner=None):
        if runner is not None:
            check_exists("$FLIMFLAM_HOME/connection_rate/client")
            check_exists("$FLIMFLAM_HOME/connection_rate/server")

    def start_client(self, runner, port):
        self.client_proc = start(f"$FLIMFLAM_HOME/connection_rate/client {port} {runner.jobs} {runner.output_dir}")

    def start_server(self, runner, port):
        self.server_proc = start(f"$FLIMFLAM_HOME/connection_rate/server {port}")

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
            "duration": runner.warmup + runner.duration,
            "cnxs": total,
        }

        return summary



class Iperf3(Workload):
    def check(self, runner=None):
        check_program("iperf3", "I can't find iperf3.  Run 'dnf install iperf3'.")

    def start_client(self, runner, port):
        self.client_proc = start(f"iperf3 --client 127.0.0.1 --port {port} --parallel {runner.jobs}"
                                 f" --json --logfile {runner.output_dir}/output.json"
                                 f" --time {runner.warmup + runner.duration} --omit {runner.warmup}")
    def stop_client(self, runner):
        # The iperf3 client will stop by itself at the conclusion of
        # the test.
        if self.client_proc is not None:
            try:
                self.client_proc.wait(timeout=10.0)
            except:
                error("Timed out waiting for iperf3 client to exit")
                super().stop_client(runner)

    def start_server(self, runner, port):
        self.server_proc = start(f"iperf3 --server --bind 127.0.0.1 --port {port}")

    def process_output(self, runner):
        output = read_json(join(runner.output_dir, "output.json"))

        summary = {
            "duration": output["end"]["sum_received"]["seconds"],
            "bits": output["end"]["sum_received"]["bytes"] * 8,
        }

        return summary

class H2load(Workload):
    def check(self, runner=None):
        check_program("h2load", "I can't find h2load.  Run 'dnf install nghttp2'.")
        check_program("nghttpd", "I can't find nghttpd.  Run 'dnf install nghttp2'.")

    def start_client(self, runner, port):
        self.client_proc = start(f"h2load --warm-up-time {runner.warmup} --duration {runner.duration}"
                                 f" --clients {runner.jobs} --threads {runner.jobs}"
                                 f" http://127.0.0.1:{port}/index.txt",
                                 stdout=join(runner.output_dir, "output.txt"))

    def start_server(self, runner, port):
        write("/tmp/flimflam/http2-server/web/index.txt", "x" * 100)
        self.server_proc = start("nghttpd 20002 --address 127.0.0.1 --no-tls"
                                 " --htdocs /tmp/flimflam/http2-server/web"
                                 f" --workers {runner.jobs}")

    def stop_client(self, runner):
        # Give h2load lots of extra time to report out
        for i in range(10):
            output = read(join(runner.output_dir, "output.txt"))

            if "time for request:" in output:
                break

            sleep(5)
        else:
            error("Timed out waiting for output")

        super().stop_client(runner)

    def process_output(self, runner):
        output = read_lines(join(runner.output_dir, "output.txt"))

        for line in output:
            if line.startswith("traffic:"):
                bits = int(line.split()[2][1:-1]) * 8
                break
        else:
            raise Exception(output)

        for line in output:
            if line.startswith("requests:"):
                operations = int(line.split()[1])
                break
        else:
            raise Exception(output)

        for line in output:
            if line.startswith("time for request:"):
                average_latency = line.split()[5]
                break
        else:
            raise Exception(output)

        data = {
            "duration": runner.duration,
            "bits": bits,
            "operations": operations,
            "latency": {
                "average": average_latency,
            }
        }

        return data

class H2loadH1(H2load):
    def check(self, runner=None):
        check_program("h2load", "I can't find h2load.  Run 'dnf install nghttp2'.")
        check_program("nginx", "I can't find nginx.  Run 'dnf install nginx'.")

    def start_client(self, runner, port):
        self.client_proc = start(f"h2load --h1 --warm-up-time {runner.warmup} --duration {runner.duration}"
                                 f" --clients {runner.jobs} --threads {runner.jobs}"
                                 f" http://127.0.0.1:{port}/index.txt",
                                 stdout=join(runner.output_dir, "output.txt"))

    def start_server(self, runner, port):
        write("/tmp/flimflam/http1-server/web/index.txt", "x" * 100)
        self.server_proc = start(f"nginx -c $FLIMFLAM_HOME/config/http1-server.conf -e /dev/stderr")

class Relay:
    def __init__(self, name, protocols):
        self.name = name
        self.protocols = protocols

        self.relay_1_proc = None
        self.relay_2_proc = None

    def check(self, runner=None):
        check_program("taskset", "I can't find taskset.  Run 'dnf install util-linux-core'.")

        if runner is not None:
            if runner.protocol not in self.protocols:
                raise PlanoError(f"Relay {self.name} doesn't support protocol {runner.protocol}")

            # XXX Check taskset config using echo

    def start_relay_1(self, runner):
        command = self.config_relay_1(runner)

        if runner.cpu_limit > 0:
            cpus = ",".join(["0", "4", "8", "12"][:runner.cpu_limit])
            command = f"taskset --cpu-list {cpus} {command}"

        self.relay_1_proc = start(command)

    def start_relay_2(self, runner):
        command = self.config_relay_2(runner)

        if runner.cpu_limit > 0:
            cpus = ",".join(["2", "6", "10", "14"][:runner.cpu_limit])
            command = f"taskset --cpu-list {cpus} {command}"

        self.relay_2_proc = start(command)

    def stop_relay_1(self, runner):
        if self.relay_1_proc is not None:
            kill(self.relay_1_proc)
            wait(self.relay_1_proc)

    def stop_relay_2(self, runner):
        if self.relay_2_proc is not None:
            kill(self.relay_2_proc)
            wait(self.relay_2_proc)

class Skrouterd(Relay):
    def check(self, runner=None):
        super().check(runner=runner)
        check_program("skrouterd", "I can't find skrouterd.  Make sure it's on the path.")

    def config_relay_1(self, runner):
        return f"skrouterd --config $FLIMFLAM_HOME/config/skrouterd-{runner.protocol}-1.conf"

    def config_relay_2(self, runner):
        return f"skrouterd --config $FLIMFLAM_HOME/config/skrouterd-{runner.protocol}-2.conf"

class Nghttpx(Relay):
    def check(self, runner=None):
        super().check(runner=runner)
        check_program("nghttpx", "I can't find nghttpx.  Run 'dnf install nghttp2'.")

    def config_relay_1(self, runner):
        if runner.protocol == "http1":
            return "nghttpx -f127.0.0.1,20001;no-tls -b127.0.0.1,10001 --workers 2 --single-process"
        elif runner.protocol == "http2":
            return "nghttpx -f127.0.0.1,20001;no-tls -b127.0.0.1,10001;/;proto=h2 --workers 2 --single-process"
        else:
            assert False

    def config_relay_2(self, runner):
        if runner.protocol == "http1":
            return "nghttpx -f127.0.0.1,10001;no-tls -b127.0.0.1,20002 --workers 2 --single-process"
        elif runner.protocol == "http2":
            return "nghttpx -f127.0.0.1,10001;no-tls -b127.0.0.1,20002;/;proto=h2 --workers 2 --single-process"
        else:
            assert False

class Nginx(Relay):
    def check(self, runner=None):
        super().check(runner=runner)

        check_program("nginx", "I can't find nginx.  Run 'dnf install nginx'.")

        if not exists("/usr/lib64/nginx/modules/ngx_stream_module.so"):
            raise PlanoError("To use Nginx as a relay, I need the stream module.  "
                             "Run 'dnf install nginx-mod-stream'.")

    def config_relay_1(self, runner):
        return f"nginx -c $FLIMFLAM_HOME/config/nginx-{runner.protocol}-1.conf -e /dev/stderr"

    def config_relay_2(self, runner):
        return f"nginx -c $FLIMFLAM_HOME/config/nginx-{runner.protocol}-2.conf -e /dev/stderr"

# sockperf under-load -i 127.0.0.1 -p 5001 --tcp
# sockperf server -i 127.0.0.1 -p 5001 --tcp

WORKLOADS = {
    "builtin": Builtin("builtin", ["tcp"]),
    "connection-rate": ConnectionRate("connection-rate", ["tcp"]),
    "iperf3": Iperf3("iperf3", ["tcp"]),
    "h2load": H2load("h2load", ["tcp"]),
    "h2load-h1": H2loadH1("h2load-h1", ["tcp"]),
}

RELAYS = {
    "skrouterd": Skrouterd("skrouterd", ["tcp"]),
    "nghttpx": Nghttpx("nghttpx", ["tcp"]),
    "nginx": Nginx("nginx", ["tcp"]),
    "none": Relay("none", ["tcp"]),
}

PROTOCOLS = [
    "tcp",
]

def print_heading(name):
    print()
    print(name.upper())
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

def print_environment():
    print_heading("Environment")

    def get_info(executable, option):
        path = which(executable)

        if path is not None:
            version = call(f"{path} {option}", quiet=True).strip()
            version = version.split("\n")[0]

            return "{} [{}]".format(path, version)

        return "-"

    def get_cpu():
        for line in read_lines("/proc/cpuinfo"):
            if line.startswith("model name"):
                return line.split(":")[1].strip()

        return "-"

    props = [
        ["Flimflam", "{} [1]".format(ARGS[0])],
        ["Skrouterd", get_info("skrouterd", "--version")],
        ["H2load", get_info("h2load", "--version")],
        ["Iperf3", get_info("iperf3", "--version")],
        ["Nghttp", get_info("nghttp", "--version")],
        ["Nginx", nvl(which("nginx"), "-")],
        ["Perf", get_info("perf", "--version")],
        ["GCC", get_info("gcc", "--version")],
        ["Distro", read("/etc/system-release").strip()],
        ["Kernel", call("uname -s -r -v", quiet=True).strip()],
        ["CPU", get_cpu()],
    ]

    print_properties(props)
