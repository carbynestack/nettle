import logging

from torch import nn

from utils.cli import CLI, Provider
from utils.spdz_pytorch_conversion import float32_tensor_to_sfloat_array, sfloat_array_to_float32_tensor


class CsModule(nn.Module):
    """Subclass of nn.Module that provides methods to store and load parameters from Amphora"""

    def __init__(self) -> None:
        super().__init__()
        self.cli = CLI(
            prime="198766463529478683931867765928436695041",
            r="141515903391459779531506841503331516415",
            r_inv="133854242216446749056083838363708373830",
            providers=[
                Provider(base_url="http://apollo.bocse.carbynestack.io/"),
                Provider(base_url="http://starbuck.bocse.carbynestack.io/")
            ])

    @staticmethod
    def __flatten(l):
        return [item for sublist in l for item in sublist]

    @staticmethod
    def __length(tensor):
        l = 1
        for dim in tensor.shape:
            l *= dim
        return l

    def store(self):
        """Serializes the model into a MP-SPDZ sfloat array and stores it in Amphora."""
        data = []
        items = self.state_dict().items()
        for layer, params in items:
            logging.info("Collecting %d parameters for layer '%s'", self.__length(params), layer)
            data += self.__flatten(float32_tensor_to_sfloat_array(params, shift=True))
        secret_id = self.cli.create_secret(values=data)
        logging.info('Uploaded %d-element model to Amphora with ID: %s', len(data), secret_id)
        return secret_id

    def __update_model(self, data):
        """Updates the model from the provided data which is expected to be a 1d array of MP-SPDZ sfloat parameters."""

        # "Reshape" to get an array of 4-element arrays (one for each MP-SPDZ sfloat).
        remaining = []
        for i in range(len(data) // 4):
            remaining.append(data[i * 4:(i + 1) * 4])

        # Traverse layers one by one updating the parameters
        for layer, params in super().state_dict().items():
            logging.info("Processing layer %s of shape %s", layer, params.shape)
            d = remaining[:self.__length(params)]
            remaining = remaining[self.__length(params):]
            t = sfloat_array_to_float32_tensor(d, params.shape, shift=True)
            params.copy_(t)
            logging.info("Copied %d parameters to layer %s", len(t), layer)

    def load(self, secret_id):
        """Loads the serialized model parameters from Amphora and updates the model accordingly."""
        values, _ = self.cli.get_secret(secret_id)
        self.__update_model(values)
