from time import sleep

from logging import DEBUG
from flwr.common.logger import log
from torch import nn

from utils.cli import CLI, Provider
from utils.spdz_pytorch_conversion import (
    float32_tensor_to_sfloat_array,
    sfloat_array_to_float32_tensor,
)


class CsModule(nn.Module):
    """Subclass of nn.Module that provides methods to store and load parameters from
    Amphora"""

    def __init__(self, request_delay: int) -> None:
        super().__init__()
        self.cli = CLI(
            prime="198766463529478683931867765928436695041",
            r="141515903391459779531506841503331516415",
            r_inv="133854242216446749056083838363708373830",
            providers=[
                Provider(base_url="http://apollo.bocse.carbynestack.io/"),
                Provider(base_url="http://starbuck.bocse.carbynestack.io/"),
            ],
        )
        self.__request_delay = request_delay
        log(
            DEBUG,
            "Initialized Carbyne Stack module with a request delay of %d seconds",
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

    def store(self):
        """Serializes the model into an MP-SPDZ sfloat array and stores it in
        Amphora."""
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
        sleep(self.__request_delay)
        secret_id = self.cli.create_secret(values=data)
        log(
            DEBUG,
            "Uploaded %d-element model to Amphora with ID: %s",
            len(data),
            secret_id,
        )
        return secret_id

    def __update_model(self, data):
        """Updates the model from the provided data which is expected to be a 1d array
        of MP-SPDZ sfloat parameters."""

        # "Reshape" to get an array of 4-element arrays (one for each MP-SPDZ sfloat).
        remaining = []
        for i in range(len(data) // 3):
            remaining.append(data[i * 3 : (i + 1) * 3])

        # Traverse layers one by one updating the parameters
        for layer, params in super().state_dict().items():
            log(DEBUG, "Processing layer %s of shape %s", layer, params.shape)
            d = remaining[: self.__length(params)]
            remaining = remaining[self.__length(params) :]
            t = sfloat_array_to_float32_tensor(d, params.shape, shift=True)
            params.copy_(t)
            log(DEBUG, "Copied %d parameters to layer %s", len(t), layer)

    def load(self, secret_id):
        """Loads the serialized model parameters from Amphora and updates the model
        accordingly."""
        log(DEBUG, "Sleeping for %d seconds", self.__request_delay)
        sleep(self.__request_delay)
        values, _ = self.cli.get_secret(secret_id)
        log(
            DEBUG,
            "Retrieved %d-element Amphora secret with ID %s",
            len(values),
            secret_id,
        )
        self.__update_model(values)
