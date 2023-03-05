# Flimflam

[![main](https://github.com/ssorj/flimflam/actions/workflows/main.yaml/badge.svg)](https://github.com/ssorj/flimflam/actions/workflows/main.yaml)

Flimflam is a tool for examining Skupper router performance.  It
combines a standard workload with scripting to capture metrics using
the Linux "perf" tools.

## Overview

<!-- * XXX Does: build the builtin workload, run the workload and relay -->
<!-- * XXX Does not: build the relay or non-builtin workload -->
<!-- * XXX The skrouterd under test is the one *you* installed -->
<!-- * XXX Skrouterd - note the number of worker threads -->

Flimflam's purpose is to enable developers to easily run router
performance tests and extract performance information, so we can make
the router faster.

Flimflam is intended to be good at:

* Capturing performance data.

* Comparing the performance of existing code with some new code you've
  written.

* Seeing how the router performs compared to other relays.

Flimflam uses the skrouterd (or nginx) on your executable path, and
skrouterd uses the Proton on your library path.  Make sure you set
`PATH` and `LD_LIBARY_PATH` as you want them - that is, where you are
installing the router and Proton under test.

Flimflam has the notion of a "relay", which is simply an abstract term
for some kind of router or reverse proxy.  You can use the `--relay`
option to change the relay for a test run.  The options are
`skrouterd`, `nginx`, and `none`.  `none` means there's no relay at
all.

A "workload" in Flimflam terms is a client and server that performs
some communication by way of the relay (if the relay is not `none`).
The options are `builtin`, `iperf3`, `h2load`, and `h2load-h1`.
`builtin` is a streaming TCP workload.  Its implementation is in the
`builtin` directory.  `h2load-h1` is a variant of `h2load` that uses
HTTP/1 only.

The workloads have some options.  `--jobs` sets the number of
concurrent communications (default 2).  `--warmup` sets the spin-up
time before measuring starts.  `--duration` sets the measurement time.

Each relay process is by default limited to 1 CPU.  Use the
`--cpu-limit` option to change this.  Workloads have no imposed limit.

**Note!**  It's important to build the router and Proton under test
with frame pointers enabled.  Otherwise, it's difficult to get
reliable call stacks for flamegraphs and perf report.

## Setting up your environment

Install required dependencies:

    sudo dnf -y install gcc js-d3-flame-graph perf sysstat util-linux-core

Install dependencies for alternative workloads and relays:

    sudo dnf -y install iperf3 nghttp2 nginx nginx-mod-stream

Enable perf events (run this as root):

    echo -1 > /proc/sys/kernel/perf_event_paranoid

Run the check command:

    ./plano check

If check says `OK`, you should be set to proceed.

## Listing commands and options

~~~
flimflam$ ./plano
usage: plano [--verbose] [--quiet] [--debug] [-h] [-f FILE] [-m MODULE] {command} ...

Run commands defined as Python functions

options:
  --verbose             Print detailed logging to the console
  --quiet               Print no logging to the console
  --debug               Print debugging output to the console
  -h, --help            Show this help message and exit
  -f FILE, --file FILE  Load commands from FILE (default '.plano.py')
  -m MODULE, --module MODULE
                        Load commands from MODULE

commands:
  {command}
    check               Check for required programs and system configuration
    run                 Run a workload without capturing any data
    stat                Capture 'perf stat' output
    skstat              Capture 'skstat' output
    record              Capture perf events using 'perf record'
    c2c                 Capture perf events using 'perf c2c'
    mem                 Capture perf events using 'perf mem'
    flamegraph          Generate a flamegraph
    bench               Run each workload on each relay and summarize the results
    build               Compile the builtin workload
    clean               Remove build artifacts and output files
    self-test           [internal]
~~~

~~~
usage: plano run [-h] [-w WORKLOAD] [-r RELAY] [-p PROTOCOL] [--jobs JOBS] [--warmup SECONDS] [--duration SECONDS] [--cpu-limit COUNT]

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

## Running a test scenario

    ./plano run
    ./plano run --workload iperf3
    ./plano run --workload h2load --relay nginx
    ./plano run --workload h2load --adaptor http2

## Recording perf data

    ./plano record
    ./plano record --workload iperf3
    ./plano record --workload h2load --relay nginx
    ./plano record --workload h2load --adaptor http2

## Using perf report

    # After recording
    perf report

## Benchmarking

    ./plano bench
