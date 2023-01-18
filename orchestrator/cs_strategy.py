from typing import Dict, Final, List, Optional, Tuple, Union

from flwr.server.client_proxy import ClientProxy
from flwr.server.strategy import FedAvg
from flwr.common import FitRes, Parameters, Scalar

MODEL_ID_CONFIG_KEY: Final[str] = "model_amphora_secret_id"


def retrieve_model_amphora_id_from_metrics(result: Tuple[ClientProxy, FitRes]) -> str:
    return result[1].metrics.get(MODEL_ID_CONFIG_KEY)

class CsStrategy(FedAvg):
    def __init__(self, initial_amphora_model_id: str) -> None:
        empty_parameters: Parameters = Parameters([], "numpy.ndarray")
        super().__init__(on_fit_config_fn=self._on_any_config_fn, on_evaluate_config_fn=self._on_any_config_fn, initial_parameters=empty_parameters)
        self._amphoraModelId: str = initial_amphora_model_id

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

        amphora_model_ids = list(map(retrieve_model_amphora_id_from_metrics, results))
        if len(amphora_model_ids) <= 0:
            raise Exception('No model secret share id received.')

        #
        # Following to be moved to ephemeral:
        #
        # # Convert results
        # weights_results = [
        #     (parameters_to_ndarrays(fit_res.parameters), fit_res.num_examples)
        #     for _, fit_res in results
        # ]
        # parameters_aggregated = ndarrays_to_parameters(aggregate(weights_results))

        # Aggregate custom metrics if aggregation fn was provided
        # metrics_aggregated = {}
        # if self.fit_metrics_aggregation_fn:
        #     fit_metrics = [(res.num_examples, res.metrics) for _, res in results]
        #     metrics_aggregated = self.fit_metrics_aggregation_fn(fit_metrics)
        # elif server_round == 1:  # Only log this warning once
        #     log(WARNING, "No fit_metrics_aggregation_fn provided")
        #
        # return parameters_aggregated, metrics_aggregated

        self._amphoraModelId = amphora_model_ids[0]
        return Parameters([], "numpy.ndarray"), {}

    @property
    def amphora_model_id(self) -> str:
        return self._amphoraModelId

    @amphora_model_id.setter
    def amphora_model_id(self, value: str):
        self._amphoraModelId = value

    def _on_any_config_fn(self, round: int) -> Dict[str, str]:
        return {MODEL_ID_CONFIG_KEY: self._amphoraModelId}
