#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from logging import DEBUG, INFO
from time import sleep

from flwr.common.logger import log
from torch import nn

from mpc_client.mpc_client import MpcClient
from utils.spdz_pytorch_conversion import (
    float32_tensor_to_sfloat_array,
    sfloat_array_to_float32_tensor,
)


class MpcModule(nn.Module):
    """Subclass of nn.Module that provides methods to store and load parameters from an MPC backend."""

    def __init__(self, mpc_client: MpcClient, request_delay: float = 0) -> None:
        """
        Creates a new :class:`MpcModule` with the given parameters.

        :param mpc_client: The :class:`MpcClient` used to talk to an MPC backend.
        :param request_delay: A non-negative delay in seconds to sleep before invoking a method call on the
         :class:`MpcClient`.
        """
        super().__init__()
        self.__mpc_client = mpc_client
        self.__request_delay = request_delay
        log(
            INFO,
            "Initialized MPC module with a request delay of %d seconds",
            self.__request_delay,
        )

    @staticmethod
    def __flatten(lst):
        return [item for sublist in lst for item in sublist]

    @staticmethod
    def __length(tensor):
        length = 1
        for dim in tensor.shape:
            length *= dim
        return length

    def __sleep(self):
        log(
            DEBUG,
            "Sleeping for %d seconds before invoking operation on MPC client",
            self.__request_delay,
        )
        sleep(self.__request_delay)

    def store(self) -> uuid.UUID:
        """
        Serializes the model into an MP-SPDZ sfloat array and stores it in the MPC backend.

        :return: The identifier of the model secret in the MPC backend.
        """
        data = []
        items = self.state_dict().items()
        for layer, params in items:
            log(
                DEBUG,
                "Collecting %d parameters for layer '%s'",
                self.__length(params),
                layer,
            )
            data += self.__flatten(float32_tensor_to_sfloat_array(params, shift=True))
        self.__sleep()
        secret_id = self.__mpc_client.create_secret(data)
        log(
            INFO,
            "Uploaded %d-element model to MPC backend with ID '%s'",
            len(data),
            secret_id,
        )
        return secret_id

    def __update_model(self, data):
        """
        Updates the model from the provided data.

        :param data: 1d array of MP-SPDZ sfloat parameters
        """
        # "Reshape" to get an array of 4-element arrays (one for each MP-SPDZ sfloat).
        remaining = []
        for i in range(len(data) // 3):
            remaining.append(data[i * 3 : (i + 1) * 3])

        # Traverse layers one by one updating the parameters
        for layer, params in super().state_dict().items():
            log(DEBUG, "Processing layer %s of shape '%s'", layer, params.shape)
            d = remaining[: self.__length(params)]
            remaining = remaining[self.__length(params) :]
            t = sfloat_array_to_float32_tensor(d, params.shape, shift=True)
            params.copy_(t)
            log(DEBUG, "Copied %d parameters to layer '%s'", len(t), layer)

    def load(self, secret_id: uuid.UUID):
        """
        Loads the serialized model parameters from the MPC backend and updates the model accordingly.

        :param secret_id: The identifier of the secret to load and update the model from
        """
        self.__sleep()
        values, _ = self.__mpc_client.get_secret(secret_id)
        log(
            INFO,
            "Retrieved %d-element secret from MPC backend with identifier '%s'",
            len(values),
            secret_id,
        )
        self.__update_model(values)
