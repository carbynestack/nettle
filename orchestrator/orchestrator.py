import uuid

import flwr as fl
from typing import Dict, Final
from flwr.server.strategy import FedAvg

MODEL_ID_CONFIG_KEY: Final[str] = "model_amphora_secret_id"


class CsStrategy(FedAvg):
    def __init__(self) -> None:
        super().__init__(on_fit_config_fn=self._on_fit_config_fn)
        self.amphoraModelId = None

    def _on_fit_config_fn(self, round: int) -> Dict[str, str]:
        return {MODEL_ID_CONFIG_KEY: self.amphoraModelId}


strategy = CsStrategy()
strategy.amphoraModelId = str(uuid.uuid4())
fl.server.start_server(config=fl.server.ServerConfig(num_rounds=1), strategy=strategy)
