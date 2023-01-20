from typing import Dict, Final, List, Optional, Tuple, Union

from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg
from flwr.common import FitRes, Parameters, Scalar
from logging import DEBUG
from flwr.common.logger import log

from utils.cli import CLI

MODEL_ID_CONFIG_KEY: Final[str] = "model_amphora_secret_id"


def retrieve_model_amphora_id_from_metrics(result: Tuple[ClientProxy, FitRes]) -> str:
    return result[1].metrics.get(MODEL_ID_CONFIG_KEY)


class CsStrategy(FedAvg):
    def __init__(
        self, cli: CLI, initial_amphora_model_id: str, number_of_clients: int
    ) -> None:
        log(
            DEBUG,
            "Initialized Carbyne Stack strategy with model id %s and %d client(s)",
            initial_amphora_model_id,
            number_of_clients,
        )
        empty_parameters: Parameters = Parameters([], "numpy.ndarray")
        super().__init__(
            min_available_clients=number_of_clients,
            min_fit_clients=number_of_clients,
            min_evaluate_clients=number_of_clients,
            on_fit_config_fn=self._on_any_config_fn,
            on_evaluate_config_fn=self._on_any_config_fn,
            initial_parameters=empty_parameters,
        )
        self.__cs_cli = cli
        self.__amphora_model_id: str = initial_amphora_model_id

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

        # Retrieve the Amphora secret IDs for the client model updates from results
        amphora_model_ids = list(map(retrieve_model_amphora_id_from_metrics, results))
        log(
            DEBUG,
            "Retrieved %d Amphora model secret IDs after round %d: %s",
            len(amphora_model_ids),
            server_round,
            amphora_model_ids,
        )
        if len(amphora_model_ids) == 0:
            raise Exception("No model secret IDs received.")

        # Invoke ephemeral with the model updates as inputs
        application_name = "ephemeral-generic.default"
        timeout = 60 * 50
        log(
            DEBUG,
            (
                "Triggering ephemeral secure aggregation (application name: %s,"
                " timeout: %d)"
            ),
            application_name,
            timeout,
        )
        aggregated_params_id = self.__cs_cli.execute(
            amphora_model_ids, application_name, timeout
        )
        log(
            DEBUG,
            "Secure aggregation created new model secret with ID: %s",
            aggregated_params_id,
        )

        self.__amphora_model_id = aggregated_params_id
        return Parameters([], "numpy.ndarray"), {}

    @property
    def amphora_model_id(self) -> str:
        return self.__amphora_model_id

    @amphora_model_id.setter
    def amphora_model_id(self, value: str):
        self.__amphora_model_id = value

    def _on_any_config_fn(self, round: int) -> Dict[str, str]:
        config = {MODEL_ID_CONFIG_KEY: self.__amphora_model_id}
        log(DEBUG, "Applying config %s for round %d", config, round)
        return config
