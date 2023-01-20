#!/usr/bin/env bash

#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

Scripts/setup-online.sh
./compile.py "${MPC_PROGRAM_NAME}.mpc"
./Player-Online.x -N 2 0 "${MPC_PROGRAM_NAME}" -OF "Player-Data/Out" &
./Player-Online.x -N 2 1 "${MPC_PROGRAM_NAME}"
