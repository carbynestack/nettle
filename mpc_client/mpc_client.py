#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from typing import List, Dict, Tuple


class MpcClient:
    """A client that talks to an MPC backend for doing I/O and for performing computations."""

    def create_secret(
        self, values: List[int], tags: Dict[str, str] = None
    ) -> uuid.UUID:
        """
        Stores the passed in values as a secret in the MPC backend.

        :param values: A non-empty arbitrary-length list of positive integers.
        :param tags: A dictionary of tags to assign the secret to in Amphora.
        :return: The identifier of the secret in UUID format
        :raises MpcClientException: An error occurred while performing the operation.
        """

    def get_secret(self, identifier: uuid.UUID) -> Tuple[List[int], Dict[str, str]]:
        """
        Retrieves the secret with the given identifier from the MPC backend.

        :param identifier: The UUID of the secret that is stored in the MPC backend
        :return: A tuple containing a list of secret values and a dictionary of tags
        :raises MpcClientException: An error occurred while performing the operation.
        """

    def execute(
        self, inputs: List[uuid.UUID], application_name: str, timeout: int = 10
    ) -> uuid.UUID:
        """
        Executes the given application in the MPC backend with the given inputs secrets.

        :param inputs: A list of secret identifiers that will be used as input to the MPC program.
        :param application_name: The name of the MPC application to be executed.
        :param timeout: Maximum time allowed for the request in seconds.  Default 10(s)
        :return: The secret identifier in UUID format
        :raises MpcClientException: An error occurred while performing the operation.
        """


class MpcClientException(Exception):
    """
    Exception raised while interacting with the MPC backend.
    """

    def __init__(self, message: str):
        """
        Creates an MpcClientException with the given message.

        :param message: explanation of the exception
        """
        self.message = message
        super().__init__(self.message)
