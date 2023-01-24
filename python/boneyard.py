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

@command(parameters=standard_params)
def sleep_(*args, **kwargs):
    """
    Measure time sleeping
    """

    try:
        read("/sys/kernel/tracing/events/sched/sched_stat_sleep/enable")
    except:
        fail("Things aren't set up yet.  See the comments in .plano.py for the sleep command.")

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
        run(f"perf record -e sched:sched_stat_sleep -e sched:sched_switch -e sched:sched_process_exit --call-graph fp --pid {pids} -o perf.data.raw sleep {kwargs['duration']}")

    results = Runner(kwargs).run(inner)

    run("perf inject -v --sched-stat -i perf.data.raw -o perf.data")
    run("perf report --stdio --show-total-period -i perf.data --call-graph none --no-children --percent-limit 1")

    remove("perf.data.raw")

    print(read(results))
