# Pellmell

Pellmell is a tool for testing Skupper router performance.  It
combines a standard workload with scripting to capture metrics using
the "perf" tools.

## Try it!

    $ ./plano         # Prints help
    $ ./plano stat
    $ ./plano flamegraph

## Installing dependencies

    dnf install gcc js-d3-flame-graph perf qpid-proton-c-devel sysstat

## Drilling into the recorded data

    $ ./plano record
    $ perf report --no-children
