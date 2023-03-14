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

from .main import *

assert "FLIMFLAM_HOME" in ENV

standard_parameters = [
    CommandParameter("workload", default="builtin", positional=False, short_option="w",
                     help="The selected workload"),
    CommandParameter("relay", default="skrouterd", positional=False, short_option="r",
                     help="The intermediary standing between the workload client and server"),
    CommandParameter("protocol", default="tcp", positional=False, short_option="p", # XXX choices
                     help="The selected protocol"),
    CommandParameter("jobs", default=2, type=int, positional=False,
                     help="The number of concurrent workload jobs"),
    CommandParameter("warmup", default=5, type=int, positional=False, metavar="SECONDS",
                     help="The warmup time in seconds"),
    CommandParameter("duration", default=5, type=int, positional=False, metavar="SECONDS",
                     help="The execution time (excluding warmup) in seconds"),
    CommandParameter("cpu_limit", default=1, type=int, positional=False, metavar="COUNT",
                     help="The max per-process relay CPU usage (0 means no limit)"),
]

bench_parameters = [
    CommandParameter("workloads", default=",".join(WORKLOADS.keys()), positional=False, short_option="w",
                     help="The selected workloads (comma-separated list)"),
    CommandParameter("relays", default=",".join(RELAYS.keys()), positional=False, short_option="r",
                     help="The selected relays (comma-separated list)"),
]

bench_parameters += standard_parameters[3:]

def check_perf():
    check_program("perf", "I can't find the perf tools.  Run 'dnf install perf'.")

    perf_event_paranoid = read("/proc/sys/kernel/perf_event_paranoid")

    if perf_event_paranoid != "-1\n":
        raise PlanoError("Perf events are not enabled.  Run 'echo -1 > /proc/sys/kernel/perf_event_paranoid' as root.")

@command
def check(ignore_perf=False):
    """
    Check for required programs and system configuration
    """

    check_program("gcc", "I can't find gcc.  Run 'dnf install gcc'.")
    check_program("pidstat", "I can't find pidstat.  Run 'dnf install sysstat'.")
    check_program("taskset", "I can't find taskset.  Run 'dnf install util-linux-core'.")

    for workload in WORKLOADS.values():
        workload.check()

    for relay in RELAYS.values():
        relay.check()

    if not ignore_perf:
        check_perf()

    print_heading("Note!")
    print("To reliably get stack traces, it is important to compile with frame pointers.")
    print("Use CFLAGS=-fno-omit-frame-pointer when compiling Proton and the router.")
    print()

def runner(kwargs, capture=None):
    if capture is None:
        def capture(pid1, pid2, duration):
            sleep(duration)

    runner = Runner(kwargs)

    output_dir = runner.run(capture)

    runner.print_summary()

    return output_dir

@command(parameters=standard_parameters)
def run_(*args, **kwargs):
    """
    Run a workload without capturing any data
    """

    runner(kwargs)
    print()

@command(parameters=standard_parameters)
def stat(*args, **kwargs):
    """
    Capture 'perf stat' output
    """

    check_perf()

    with temp_file() as output:
        def capture(pid1, pid2, duration):
            run(f"perf stat --detailed --pid {pid1},{pid2} sleep {duration}", output=output)

        runner(kwargs, capture)
        print(read(output))

@command(parameters=standard_parameters)
def skstat(*args, **kwargs):
    """
    Capture 'skstat' output
    """

    check_program("skstat", "I can't find skstat.  Make sure it's on the path.")

    if kwargs["relay"] != "skrouterd":
        fail("The skstat command works with skrouterd only")

    with temp_file() as output1, temp_file() as output2:
        def capture(pid1, pid2, duration):
            sleep(duration)
            run(f"skstat -b localhost:56721 -m", stdout=output1)
            run(f"skstat -b localhost:56722 -m", stdout=output2)

        runner(kwargs, capture)

        print_heading("Router 1")
        print(read(output1))
        print_heading("Router 2")
        print(read(output2))

@command(parameters=standard_parameters)
def record(*args, **kwargs):
    """
    Capture perf events using 'perf record'
    """

    check_perf()

    def capture(pid1, pid2, duration):
        run(f"perf record --freq 997 --call-graph fp --pid {pid1},{pid2} sleep {duration}")

    runner(kwargs, capture)

    print_heading("Next step")
    print("Run 'perf report --no-children'")
    print()

@command(parameters=standard_parameters)
def c2c(*args, **kwargs):
    """
    Capture perf events using 'perf c2c'
    """

    check_perf()

    def capture(pid1, pid2, duration):
        run(f"perf c2c record --freq 997 --call-graph fp --pid {pid1},{pid2} sleep {duration}")

    runner(kwargs, capture)

    print_heading("Next step")
    print("Run 'perf c2c report'")
    print()

@command(parameters=standard_parameters)
def mem(*args, **kwargs):
    """
    Capture perf events using 'perf mem'
    """

    check_perf()

    def capture(pid1, pid2, duration):
        run(f"perf mem record --freq 997 --call-graph fp --pid {pid1},{pid2} sleep {duration}")

    runner(kwargs, capture)

    print_heading("Next step")
    print("Run 'perf mem report --no-children'")
    print()

@command(parameters=standard_parameters)
def flamegraph(*args, **kwargs):
    """
    Generate a flamegraph
    """

    try:
        check_exists("/usr/share/d3-flame-graph")
    except:
        fail("I can't find d3-flame-graph.  Run 'dnf install js-d3-flame-graph'.")

    check_perf()

    if exists("flamegraph.html"):
        move("flamegraph.html", "old.flamegraph.html")

    def capture(pid1, pid2, duration):
        run(f"perf script flamegraph --freq 997 --call-graph fp --pid {pid1},{pid2} sleep {duration}")

    runner(kwargs, capture)

    print_heading("Next step")

    print("Go to {} in your browser".format(get_file_url("flamegraph.html")))
    print()

@command(parameters=bench_parameters)
def bench(*args, **kwargs):
    """
    Run each workload on each relay and summarize the results
    """

    workloads = [x for x in WORKLOADS.values() if x.name in kwargs["workloads"].split(",")]
    relays = [x for x in RELAYS.values() if x.name in kwargs["relays"].split(",")]

    for workload in workloads:
        workload.check()

    for relay in relays:
        relay.check()

    data = [["Workload", "Relay", "Protocol", "Bits/s", "Ops/s", "Lat*", "R1 CPU", "R1 RSS", "R2 CPU", "R2 RSS"]]

    for workload in workloads:
        for relay in relays:
            for protocol in PROTOCOLS:
                if protocol not in workload.protocols:
                    continue

                if protocol not in relay.protocols:
                    continue

                kwargs["workload"] = workload.name
                kwargs["relay"] = relay.name
                kwargs["protocol"] = protocol

                output_dir = runner(kwargs)
                print()

                summary = read_json(join(output_dir, "summary.json"))
                results = summary["results"]
                bps, ops, lat = None, None, None
                r1cpu, r1rss, r2cpu, r2rss = None, None, None, None

                if "bits" in results:
                    bps = format_quantity(results["bits"] / results["duration"])

                if "operations" in results:
                    ops = format_quantity(results["operations"] / results["duration"])

                if "latency" in results:
                    lat = results["latency"]["average"]

                if "resources" in summary:
                    r1cpu = format_percent(summary["resources"]["relay_1"]["average_cpu"])
                    r1rss = format_quantity(summary["resources"]["relay_1"]["max_rss"], mode="binary")
                    r2cpu = format_percent(summary["resources"]["relay_2"]["average_cpu"])
                    r2rss = format_quantity(summary["resources"]["relay_2"]["max_rss"], mode="binary")

                data.append([workload.name, relay.name, protocol, bps, ops, lat, r1cpu, r1rss, r2cpu, r2rss])

    print("---")
    print_heading("Benchmark results")
    print_table(data, "lllr")
    print()
