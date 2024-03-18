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

from .main import *
from . import commands

standard_options = [
    "--duration", "2",
    "--warmup", "1",
    "--jobs", "1",
    "--cpu-limit", "0"
]

def perf_enabled():
    try:
        commands.check_perf()
    except:
        return False

    return True

def run_command(command):
    with working_dir():
        PlanoCommand(commands).main([command] + standard_options)

def run_workload(workload):
    with working_dir():
        PlanoCommand(commands).main(["run", "--workload", workload, "--relay", "none"] + standard_options)

def run_relay(relay):
    for protocol in RELAYS[relay].protocols:
        with working_dir():
            PlanoCommand(commands).main(["run", "--relay", relay, "--protocol", protocol] + standard_options)

@test
def command_executable():
    run("flimflam --help run")

@test
def command_options():
    PlanoCommand(commands).main(["--help"])

@test
def command_check():
    if perf_enabled():
        PlanoCommand(commands).main(["check"])
    else:
        PlanoCommand(commands).main(["check", "--ignore-perf"])

@test
def command_run():
    run_command("run")

@test
def command_record():
    if not perf_enabled():
        skip_test("The perf tools are not enabled")

    run_command("record")

@test
def command_stat():
    if not perf_enabled():
        skip_test("The perf tools are not enabled")

    run_command("stat")

@test
def command_skstat():
    run_command("skstat")

@test
def command_flamegraph():
    if not perf_enabled():
        skip_test("The perf tools are not enabled")

    run_command("flamegraph")

@test
def command_c2c():
    if not perf_enabled():
        skip_test("The perf tools are not enabled")

    run_command("c2c")

@test
def command_mem():
    if not perf_enabled():
        skip_test("The perf tools are not enabled")

    run_command("mem")

@test
def workload_builtin():
    run_workload("builtin")

@test
def workload_iperf3():
    run_workload("iperf3")

@test
def workload_h2load():
    run_workload("h2load")

@test
def workload_h2load_h1():
    run_workload("h2load-h1")

@test
def relay_none():
    run_relay("none")

@test
def relay_skrouterd():
    run_relay("skrouterd")

@test
def relay_nghttpx():
    run_relay("nghttpx")

@test
def relay_nginx():
    run_relay("nginx")

@test
def bench():
    run_command("bench")
