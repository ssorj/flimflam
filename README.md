# Flimflam

[![main](https://github.com/ssorj/flimflam/actions/workflows/main.yaml/badge.svg)](https://github.com/ssorj/flimflam/actions/workflows/main.yaml)

Flimflam is a tool for examining Skupper router performance.  It
combines a standard workload with scripting to capture metrics using
the Linux "perf" tools.

## Things to know

* Flimflam uses the skrouterd (or nginx) on your path.
* Relays
** Each relay process is by default limited to 1 CPU.  Use the `--cpu-limit` option to change this.  Workloads have no imposed limit.
* Workloads
* ./plano --help
* ./plano run
* Common arguments
* ./plano stat
* ./plano record
* ./plano flamegraph
* ./plano bench
* Frame pointers
* Tips for using 'perf report'

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



## Drilling into the recorded data

    $ ./plano record
    $ perf report --no-children
