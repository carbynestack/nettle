#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as f

from model.mpc_model import MpcModule
from mpc_client.mpc_client import MpcClient


class Net(MpcModule):
    """
    Model used for the CIFAR-10 federated learning experiment (simple CNN adapted from 'PyTorch: A 60-Minute Blitz')
    """

    def __init__(
        self, mpc_client: MpcClient, request_delay: Optional[int] = None
    ) -> None:
        """
        Instantiates a :class:`Net` model with the MPC client.

        :param mpc_client: The :class:`MpcClient` used to talk to an MPC backend.
        :param request_delay: A non-negative delay in seconds to sleep before invoking a method call on the
            :class:`MpcClient`.
        """
        super().__init__(mpc_client, 0 if request_delay is None else request_delay)
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Performs a single forward pass of the input tensor through the network.

        :param x: The input tensor used to perform the forward pass
        :return: The result tensor
        """
        x = self.pool(f.relu(self.conv1(x)))
        x = self.pool(f.relu(self.conv2(x)))
        x = x.view(-1, 16 * 5 * 5)
        x = f.relu(self.fc1(x))
        x = f.relu(self.fc2(x))
        return self.fc3(x)
