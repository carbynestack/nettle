#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from typing import Dict, Final, List, Optional, Tuple, Union

from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg
from flwr.common import FitRes, Parameters, Scalar
from logging import DEBUG
from flwr.common.logger import log

from mpc_client.mpc_client import MpcClient

#: The key used for storing the identifier of the model secret in flower control structures, e.g., FitRes
MODEL_ID_CONFIG_KEY: Final[str] = "model_secret_id"


class MpcStrategy(FedAvg):
    """
    A :class:`flwr.server.strategy.strategy.Strategy` that uses an MPC backend as the model store and for Secure
    Aggregation.
    """

    def __init__(
        self,
        mpc_client: MpcClient,
        mpc_application_name: str,
        initial_model_id: uuid.UUID,
        number_of_clients: int,
    ) -> None:
        """
        Instantiates :class:`MpcStrategy` with the given arguments.

        :param mpc_client: The :class:`MpcClient` used to talk to the MPC backend
        :param mpc_application_name: The name of the MPC application used to perform the secure aggregation
        :param initial_model_id: The identifier of the secret in the MPC backend that contains the initial model
        :param number_of_clients: The number of clients expected by the orchestrator
        """
        log(
            DEBUG,
            "Initialized MPC strategy with MPC application name '%s' model id '%s' and %d client(s)",
            mpc_application_name,
            initial_model_id,
            number_of_clients,
        )
        empty_parameters: Parameters = Parameters([], "numpy.ndarray")
        super().__init__(
            min_available_clients=number_of_clients,
            min_fit_clients=number_of_clients,
            min_evaluate_clients=number_of_clients,
            on_fit_config_fn=self.__on_any_config_fn,
            on_evaluate_config_fn=self.__on_any_config_fn,
            initial_parameters=empty_parameters,
        )
        self.__mpc_client = mpc_client
        self.__mpc_application_name = mpc_application_name
        self.__model_id = initial_model_id

    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """Aggregate fit results using weighted average."""
        if not results:
            return None, {}
        # Do not aggregate if there are failures and failures are not accepted
        if not self.accept_failures and failures:
            return None, {}

        # Retrieve the identifiers of the secrets for the client model updates from results
        secret_model_ids = list(map(self.__retrieve_model_id_from_metrics, results))
        log(
            DEBUG,
            "Retrieved %d model secret IDs after round %d: %s",
            len(secret_model_ids),
            server_round,
            secret_model_ids,
        )
        if len(secret_model_ids) == 0:
            raise Exception("No model secret IDs received.")

        # Invoke MPC backend with the model updates as inputs
        # TODO Make this configurable
        timeout = 60 * 50
        log(
            DEBUG,
            "Triggering MPC secure aggregation with application name '%s' and timeout '%d')",
            self.__mpc_application_name,
            timeout,
        )
        aggregated_params_id = self.__mpc_client.execute(
            secret_model_ids, self.__mpc_application_name, timeout
        )
        log(
            DEBUG,
            "Secure aggregation created new model secret with identifier '%s'",
            aggregated_params_id,
        )

        self.__model_id = aggregated_params_id
        return Parameters([], "numpy.ndarray"), {}

    @property
    def amphora_model_id(self) -> uuid.UUID:
        return self.__model_id

    @amphora_model_id.setter
    def amphora_model_id(self, value: uuid.UUID):
        self.__model_id = value

    def __on_any_config_fn(self, round: int) -> Dict[str, str]:
        config = {MODEL_ID_CONFIG_KEY: str(self.__model_id)}
        log(DEBUG, "Applying config %s for round %d", config, round)
        return config

    @staticmethod
    def __retrieve_model_id_from_metrics(
        result: Tuple[ClientProxy, FitRes]
    ) -> uuid.UUID:
        return uuid.UUID(result[1].metrics.get(MODEL_ID_CONFIG_KEY))
