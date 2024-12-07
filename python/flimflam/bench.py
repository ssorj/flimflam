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
from dataclasses import dataclass as _dataclass

def _run_scenario(kwargs):
    def capture(pid1, pid2, duration, call_graph):
        sleep(duration)

    runner = Runner(kwargs)

    output_dir = runner.run(capture)

    runner.print_summary()

    return output_dir

def run(workloads, relays, kwargs):
    for workload in workloads:
        workload.check()

    for relay in relays:
        relay.check()

    data = [["Workload", "Relay", "Protocol", "Bits/s", "Ops/s", "Lat*", "R1 CPU", "R1 RSS", "R2 CPU", "R2 RSS"]]

    for workload in workloads:
        for relay in relays:
            if workload.name == 'connection-rate' :
                if not relay.name == 'skrouterd' :
                    continue

            for protocol in PROTOCOLS:
                if protocol not in workload.protocols:
                    continue

                if protocol not in relay.protocols:
                    continue

                kwargs["workload"] = workload.name
                kwargs["relay"] = relay.name
                kwargs["protocol"] = protocol

                output_dir = _run_scenario(kwargs)
                print()

                summary = read_json(join(output_dir, "summary.json"))
                results = summary["results"]
                bps, ops, lat = None, None, None
                r1cpu, r1rss, r2cpu, r2rss = None, None, None, None

                if "bits" in results:
                    bps = format_quantity(results["bits"] / results["duration"])
                
                # In the case of Connection Rate, overload the 'bps' field to 
                # mean 'connections per second', so it will fit in the benchmark
                # chart with everything else.
                if "cnxs" in results:
                    bps = format_quantity(results["cnxs"] / results["duration"])

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
    print_environment()
    print_heading("Benchmark results")
    _print_table(data, "lllr")
    print()

def _print_table(data, align=None):
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
