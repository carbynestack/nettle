from typing import Dict, Final
from flwr.server.strategy import FedAvg

MODEL_ID_CONFIG_KEY: Final[str] = "model_amphora_secret_id"

class CsStrategy(FedAvg):
    def __init__(self) -> None:
        super().__init__(on_fit_config_fn=self._on_fit_config_fn)
        self._amphoraModelId: str = None

    @property
    def amphora_model_id(self) -> str:
        return self._amphoraModelId

    @amphora_model_id.setter
    def amphora_model_id(self, value: str):
        self._amphoraModelId = value

    def _on_fit_config_fn(self, round: int) -> Dict[str, str]:
        return {MODEL_ID_CONFIG_KEY: self._amphoraModelId}
