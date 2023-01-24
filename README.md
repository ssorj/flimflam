# Flimflam

Flimflam is a tool for examining Skupper router performance.  It
combines a standard workload with scripting to capture metrics using
the Linux "perf" tools.

## Things to know

* Flimflam uses the skrouterd (or nginx) on your path.
* Relays
* Workloads
* ./plano --help
* ./plano check
* ./plano run
* ./plano stat
* ./plano record
* ./plano flamegraph
* ./plano bench
* Frame pointers
* Tips for using 'perf report'

## Installing dependencies

    # Required
    dnf install gcc js-d3-flame-graph perf sysstat util-linux-core

    # For alternative workloads and relays
    dnf install iperf3 nghttp2 nginx nginx-mod-stream

## Drilling into the recorded data

    $ ./plano record
    $ perf report --no-children
