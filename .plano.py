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

from bullseye import *

project.name = "flimflam"
project.data_dirs = ["builtin", "config", "connection_rate"]
project.test_modules = ["flimflam.tests"]

@command(parent=build)
def build(*args, **kwargs):
    parent(*args, **kwargs)

    check_program("gcc", "I can't find gcc.  Run 'dnf install gcc'.")

    run("gcc builtin/client.c -o build/flimflam/builtin/client -g -O2 -std=c99 -fno-omit-frame-pointer")
    run("gcc builtin/server.c -o build/flimflam/builtin/server -g -O2 -std=c99 -fno-omit-frame-pointer")

    run("gcc connection_rate/client.c -o build/flimflam/connection_rate/client -g -O2 -std=c99 -fno-omit-frame-pointer")
    run("gcc connection_rate/server.c -o build/flimflam/connection_rate/server -g -O2 -std=c99 -fno-omit-frame-pointer")
