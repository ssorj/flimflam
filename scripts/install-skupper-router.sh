#!/bin/sh
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

set -Ceu

if [ -n "${BASH:-}" ]
then
    set -E -o pipefail -o posix +o braceexpand
    test -n "${POSIXLY_CORRECT}"
fi

PREFIX=$HOME/.local

export LIBRARY_PATH=$PREFIX/lib64
export C_INCLUDE_PATH=$PREFIX/include
export CPLUS_INCLUDE_PATH=$C_INCLUDE_PATH
export LD_LIBRARY_PATH=$LIBRARY_PATH

cd $(mktemp -d)

git clone --depth 1 https://github.com/apache/qpid-proton.git

mkdir -p proton-build

(
    cd proton-build

    cmake ../qpid-proton -DCMAKE_INSTALL_PREFIX=$PREFIX -DENABLE_WARNING_ERROR=OFF -DBUILD_TLS=ON -DBUILD_CPP=OFF

    make -j $(nproc) && make install
)

git clone --depth 1 https://github.com/skupperproject/skupper-router.git

mkdir -p router-build

(
    cd router-build

    cmake ../skupper-router -DCMAKE_INSTALL_PREFIX=$PREFIX -DProton_DIR=$PREFIX/lib64/cmake/Proton

    make -j $(nproc) && make install
)
