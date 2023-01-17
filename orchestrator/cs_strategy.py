from typing import Dict, Final, List
from flwr.server.strategy import FedAvg
from flwr.common import Parameters, NDArray, NDArrays
from numpy import ndarray

MODEL_ID_CONFIG_KEY: Final[str] = "model_amphora_secret_id"

class CsStrategy(FedAvg):
    def __init__(self, initial_amphora_model_id: str) -> None:
        empty_parameters: Parameters = Parameters([], "numpy.ndarray")
        super().__init__(on_fit_config_fn=self._on_fit_config_fn, initial_parameters=empty_parameters)
        self._amphoraModelId: str = initial_amphora_model_id

    @property
    def amphora_model_id(self) -> str:
        return self._amphoraModelId

    @amphora_model_id.setter
    def amphora_model_id(self, value: str):
        self._amphoraModelId = value

    def _on_fit_config_fn(self, round: int) -> Dict[str, str]:
        return {MODEL_ID_CONFIG_KEY: self._amphoraModelId}
