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

router1_config = """
router {
    mode: interior
    id: router1
}

listener {
    host: localhost
    port: 20001
    saslMechanisms: ANONYMOUS
}

connector {
   host: localhost
   port: 45672
   role: inter-router
}

tcpListener {
    address: flimflam/tcp
    host: localhost
    port: 45673
}
"""

router2_config = """
router {
    mode: interior
    id: router2
}

listener {
    host: localhost
    port: 20002
    saslMechanisms: ANONYMOUS
}

listener {
    host: localhost
    port: 45672
    role: inter-router
}

tcpConnector {
    address: flimflam/tcp
    host: localhost
    port: 45674
}
"""

router1_config_file = write(make_temp_file(), router1_config)
router2_config_file = write(make_temp_file(), router2_config)

standard_args = (
    CommandArgument("duration", default=5, positional=False,
                    help="The time to run (excluding warmup) in seconds"),
    CommandArgument("warmup", default=5, positional=False,
                    help="Warmup time in seconds"),
    CommandArgument("jobs", default=2, positional=False,
                    help="The number of concurrent client workloads"),
    CommandArgument("buffer", default=16384, positional=False, metavar="SIZE",
                    help="The TCP send and receive buffer size in bytes"),
)

@command
def check():
    """
    Check for required programs and system configuration
    """
    check_program("gcc", "I can't find gcc.  Run 'dnf install gcc'.")
    check_program("perf", "I can't find the perf tools.  Run 'dnf install perf'.")
    check_program("pidstat", "I can't find pidstat.  Run 'dnf install sysstat'.")
    check_program("skrouterd", "I can't find skrouterd.  Make sure it is on the path.")

    perf_event_paranoid = read("/proc/sys/kernel/perf_event_paranoid")

    if perf_event_paranoid != "-1\n":
        exit("Perf events are not enabled.  Run 'echo -1 > /proc/sys/kernel/perf_event_paranoid' as root.")

@command
def clean():
    """
    Remove build artifacts and output files
    """
    remove("client")
    remove("server")
    remove("perf.data")
    remove("perf.data.old")
    remove("perf.data.raw")
    remove("perf.data.raw.old")
    remove("flamegraph.html")
    remove("flamegraph.html.old")
    remove(list_dir(".", "transfers.*.csv"))

@command
def build():
    """
    Compile the load generator
    """
    check()

    run("gcc client.c -o client -g -O2 -std=c99 -fno-omit-frame-pointer")
    run("gcc server.c -o server -g -O2 -std=c99 -fno-omit-frame-pointer")

def run_outer(inner, jobs, warmup, buffer):
    procs = list()

    with start(f"skrouterd --config {router1_config_file}") as router1, \
         start(f"skrouterd --config {router2_config_file}") as router2:
        await_port(45673)

        procs.append(start(f"./server 45674 {buffer}"))

        # Without a sleep here, the router closes the client
        # connections because the server isn't ready yet.
        sleep(1)

        procs.append(start(f"./client 45673 {buffer} {jobs}"))

        pids = [router1.pid, router2.pid] + [x.pid for x in procs]
        pids = ",".join([str(x) for x in pids])

        try:
            with start(f"pidstat 2 --human -t -p {pids}"):
                sleep(warmup)
                inner(pids)
        finally:
            for proc in procs:
                kill(proc)

def print_transfers(jobs, duration):
    total = 0

    for i in range(jobs):
        line = tail(f"transfers.{i}.csv", 1)
        values = line.split(",", 2)

        try:
            total += int(values[2])
        except IndexError:
            print("ERROR: Unexpected transfer value:", values)

    print(f">>> {total:,} bytes <<<")

@command(args=standard_args)
def stat(jobs, duration, warmup, buffer):
    """
    Capture 'perf stat' output
    """
    build()

    with temp_file() as output:
        def inner(pids):
            run(f"perf stat --detailed --pid {pids} sleep {duration}", output=output)

        run_outer(inner, jobs, warmup, buffer)

        print(read(output))

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def flamegraph(jobs, duration, warmup, buffer):
    """
    Generate a flamegraph
    """
    try:
        check_exists("/usr/share/d3-flame-graph")
    except:
        fail("I can't find d3-flame-graph.  Run 'dnf install js-d3-flame-graph'.")

    build()

    def inner(pids):
        if exists("flamegraph.html"):
            move("flamegraph.html", "flamegraph.html.old")

        run(f"perf script flamegraph --freq 997 --call-graph dwarf --pid {pids} sleep {duration}")

    run_outer(inner, jobs, warmup, buffer)

    print(get_file_url("flamegraph.html"))

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def record(jobs, duration, warmup, buffer):
    """
    Capture perf events using 'perf record'
    """
    build()

    def inner(pids):
        run(f"perf record --freq 997 --call-graph dwarf --pid {pids} sleep {duration}")

    run_outer(inner, jobs, warmup, buffer)

    run("perf report --stdio --call-graph none --no-children --percent-limit 1")

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def c2c(jobs, duration, warmup, buffer):
    """
    Capture perf events using 'perf c2c'
    """
    build()

    def inner(pids):
        run(f"perf c2c record --freq 997 --call-graph dwarf --pid {pids} sleep {duration}")

    run_outer(inner, jobs, warmup, buffer)

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def mem(jobs, duration, warmup, buffer):
    """
    Capture perf events using 'perf mem'
    """
    build()

    def inner(pids):
        run(f"perf mem record --freq 997 --call-graph dwarf --pid {pids} sleep {duration}")

    run_outer(inner, jobs, warmup, buffer)

    run("perf mem report --stdio --call-graph none --no-children --percent-limit 1")

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def sleep_(jobs, duration, warmup, buffer):
    """
    Measure time sleeping
    """
    try:
        read("/sys/kernel/tracing/events/sched/sched_stat_sleep/enable")
    except:
        fail("Things aren't set up yet.  See the comments in .planofile for sleep.")

        # Need:
        #
        # sudo chmod -R o+r /sys/kernel/tracing
        # sudo find /sys/kernel/tracing -type d -exec chmod o+x {} \;
        #
        # And:
        #
        # sudo sysctl kernel.sched_schedstats=1

    build()

    def inner(pids):
        run(f"perf record -e sched:sched_stat_sleep -e sched:sched_switch -e sched:sched_process_exit --call-graph dwarf --pid {pids} -o perf.data.raw sleep {duration}")

    run_outer(inner, jobs, warmup, buffer)

    run("perf inject -v --sched-stat -i perf.data.raw -o perf.data")
    run("perf report --stdio --show-total-period -i perf.data --call-graph none --no-children --percent-limit 1")

    print_transfers(jobs, duration + warmup)

@command(args=standard_args)
def skstat(jobs, duration, warmup, buffer):
    """
    Capture 'skstat' output
    """
    build()

    def inner(pids):
        run(f"sleep {duration}")
        run(f"skstat -b localhost:20001 -m")

    run_outer(inner, jobs, warmup, buffer)

    print_transfers(jobs, duration + warmup)

@command
def self_test():
    """
    Test Flimflam
    """
    flamegraph(duration=1, warmup=0.1, jobs=1, buffer=16384)
    stat(duration=1, warmup=0.1, jobs=1, buffer=16384)
    record(duration=1, warmup=0.1, jobs=1, buffer=16384)
    clean()