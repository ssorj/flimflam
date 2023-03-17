# Flimflam

[![main](https://github.com/ssorj/flimflam/actions/workflows/main.yaml/badge.svg)](https://github.com/ssorj/flimflam/actions/workflows/main.yaml)

Flimflam is a tool for examining Skupper router performance.  It
combines a standard workload with scripting to capture metrics using
the Linux "perf" tools.

## Overview

Flimflam's purpose is to enable developers to easily run router
performance tests and extract performance information, so we can make
the router faster.

Flimflam is intended to be good at:

* Capturing performance data.

* Comparing the performance of existing code with new code you've
  written.

* Seeing how the router performs compared to other relays.

Flimflam uses the skrouterd on your executable path, and skrouterd
uses the Proton on your library path.  Make sure you set `PATH` and
`LD_LIBARY_PATH` as you want them - that is, where you are installing
the router and Proton under test.

Flimflam has the notion of a "relay", which is simply an abstract term
for some kind of router or reverse proxy.  You can use the `--relay`
option to change the relay for a test run.  The options are
`skrouterd`, `nghttpx`, `nginx`, and `none`.  `none` means there's no
relay at all.

A "workload" in Flimflam terms is a client and server that performs
some communication by way of the relays.  The options are `builtin`,
`iperf3`, `h2load`, and `h2load-h1`.  `builtin` is a streaming TCP
workload.  Its implementation is in the `builtin` directory.  `iperf3`
is a widely used TCP benchmarking tool.  `h2load` is an HTTP/2
benchmaring took.  `h2load-h1` is a variant of `h2load` that uses
HTTP/1 only.

The workloads have common options.  `--jobs` sets the number of
concurrent communications (default 2).  `--warmup` sets the spin-up
time before measuring starts (default 5 seconds).  `--duration` sets
the measurement time (default 5 seconds).

There are two relays standing between the workload client and server:

~~~
C -> R1 -> R2 -> S
~~~

Each relay process is by default limited to 1 CPU.  Use the
`--cpu-limit` option to change this.  Workloads have no imposed limit.

**Note!**  It's important to build the router and Proton under test
with frame pointers enabled.  Otherwise, it's difficult to get
reliable call stacks for flamegraphs and perf report.

## Installation

Install required dependencies:

    sudo dnf -y install gcc js-d3-flame-graph perf sysstat util-linux-core

Install dependencies for alternative workloads and relays:

    sudo dnf -y install iperf3 nghttp2 nginx nginx-mod-stream

Install Flimflam itself.  The resulting executable is at
`~/.local/bin/flimflam`.

    cd flimflam
    ./plano install

Enable perf events (run this as root):

    echo -1 > /proc/sys/kernel/perf_event_paranoid

Run the check command:

    flimflam check

If check says `OK`, you should be set to proceed.

## Commands and options

### flimflam

~~~
usage: flimflam [--verbose] [--quiet] [--debug] [-h] {command} ...

A tool for examining Skupper router performance

options:
  --verbose   Print detailed logging to the console
  --quiet     Print no logging to the console
  --debug     Print debugging output to the console
  -h, --help  Show this help message and exit

commands:
  {command}
    check     Check for required programs and system configuration
    run       Run a workload without capturing any data
    stat      Capture 'perf stat' output
    skstat    Capture 'skstat' output
    record    Capture perf events using 'perf record'
    c2c       Capture perf events using 'perf c2c'
    mem       Capture perf events using 'perf mem'
    flamegraph
              Generate a flamegraph
    bench     Run each workload on each relay and summarize the results
~~~

### flimflam run

The perf event commands have these options plus some that are
perf-specific.

~~~
usage: flimflam run [-h] [-w WORKLOAD] [-r RELAY] [-p PROTOCOL] [--jobs JOBS] [--warmup SECONDS] [--duration SECONDS] [--cpu-limit COUNT]

Run a workload without capturing any data

options:
  -h, --help            Show this help message and exit
  -w WORKLOAD, --workload WORKLOAD
                        The selected workload (default 'builtin')
  -r RELAY, --relay RELAY
                        The intermediary standing between the workload client and server (default 'skrouterd')
  -p PROTOCOL, --protocol PROTOCOL
                        The selected protocol (default 'tcp')
  --jobs JOBS           The number of concurrent workload jobs (default 2)
  --warmup SECONDS      The warmup time in seconds (default 5)
  --duration SECONDS    The execution time (excluding warmup) in seconds (default 5)
  --cpu-limit COUNT     The max per-process relay CPU usage (0 means no limit) (default 1)
~~~

### flimflam bench

~~~
usage: flimflam bench [-h] [-w WORKLOADS] [-r RELAYS] [--jobs JOBS] [--warmup SECONDS] [--duration SECONDS] [--cpu-limit COUNT]

Run each workload on each relay and summarize the results

options:
  -h, --help            Show this help message and exit
  -w WORKLOADS, --workloads WORKLOADS
                        The selected workloads (comma-separated list) (default 'builtin,iperf3,h2load,h2load-h1')
  -r RELAYS, --relays RELAYS
                        The selected relays (comma-separated list) (default 'skrouterd,nghttpx,nginx,none')
  --jobs JOBS           The number of concurrent workload jobs (default 2)
  --warmup SECONDS      The warmup time in seconds (default 5)
  --duration SECONDS    The execution time (excluding warmup) in seconds (default 5)
  --cpu-limit COUNT     The max per-process relay CPU usage (0 means no limit) (default 1)
~~~

## Running a single test scenario

    flimflam run # Default workload, relay, and protocol are 'builtin', 'skrouterd', and 'tcp'
    flimflam run --workload iperf3
    flimflam run --workload h2load --relay nginx
    flimflam run --workload h2load --protocol http2

## Recording perf data

These produce a `perf.data` file in the current directory.

    flimflam record
    flimflam record --workload iperf3
    flimflam record --workload h2load --relay nginx
    flimflam record --workload h2load --protocol http2

After recording, you can use `perf report` to inspect the results.
The `--no-children` option sorts the results by each function's own
time, excluding that of its child calls.

    perf report --no-children

## Generating flamegraphs

These produce a `flamegraph.html` file in the current directory.

    flimflam flamegraph
    flimflam flamegraph --workload h2load-h1 --protocol http1

## Benchmarking

    flimflam bench
    flimflam bench --relays skrouterd
    flimflam bench --workloads builtin,iperf3

## Ideas to consider

Try compiling with `CFLAGS=-fno-inline` before you capture data.  This
will overstate the cost of small, frequently called functions, but it
can also help you better isolate where your program is spending time.
You can look at the annotated instructions in `perf report` to
distinguish call overhead from more interesting stuff.

Try to look at your program from both ends: top down and bottom up.
Flamegraphs are very nice for the former, and `perf report
--no-children` is good for the latter.  Flamegraphs give you a broad
strokes picture of where your program is spending time.
`--no-children` highlights costs that occur at many different leaf
nodes.

Once you determine that a particular function is important, try
optimizing it in isolation.  Refactor the code, and for each
iteration, use `objdump --disassemble` to look at the resulting
instructions.  Check that the inlining you want is indeed in effect.
Watch the instruction count change with each iteration.

If your flamegraphs look messed up, and you have an Intel or newer AMD
machine, try using the `--call-graph lbr` option.
