#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import uuid
from logging import DEBUG
from typing import Dict, Tuple

import flwr as fl
from flwr.common import NDArrays, Scalar
from flwr.common.logger import log
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm

from model.mpc_model import MpcModule
from orchestrator.mpc_strategy import MODEL_ID_CONFIG_KEY


class NettleClient(fl.client.NumPyClient):
    """A Client in the Nettle federated learning system."""

    def __init__(
        self,
        device: torch.device,
        net: MpcModule,
        train_loader: DataLoader,
        test_loader: DataLoader,
    ):
        """
        Instantiates an :class:`NettleClient` with the given device, model, and training/test datasets.

        :param device: The :class:`torch.device` used to perform the training on the local dataset
        :param net: The network (subclass of :class:`MpcModule`) to be trained
        :param train_loader: The :class:`DataLoader` use to load the training dataset
        :param test_loader: The :class:`DataLoader` use to load the test dataset
        """
        self.__device = device
        self.__net = net
        self.__train_loader = train_loader
        self.__test_loader = test_loader

    def train(self, epochs: int):
        """
        Performs training for the given number of epochs.

        :param epochs: The number of training epochs
        """
        criterion = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.SGD(self.__net.parameters(), lr=0.001, momentum=0.9)
        for epoch in range(epochs):
            log(DEBUG, "Starting training epoch %d/%d", epoch, epochs)
            for images, labels in tqdm(self.__train_loader):
                optimizer.zero_grad()
                criterion(
                    self.__net(images.to(self.__device)), labels.to(self.__device)
                ).backward()
                optimizer.step()

    def test(self) -> (float, float):
        """
        Validates the model using the test dataset.

        :return: The average loss and the accuracy
        """
        criterion = torch.nn.CrossEntropyLoss()
        correct, total, loss = 0, 0, 0.0
        with torch.no_grad():
            for images, labels in tqdm(self.__test_loader):
                outputs = self.__net(images.to(self.__device))
                labels = labels.to(self.__device)
                loss += criterion(outputs, labels).item()
                total += labels.size(0)
                correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()
        return loss / len(self.__test_loader.dataset), correct / total

    def get_parameters(self, config: Dict[str, Scalar]) -> NDArrays:
        return [val.cpu().numpy() for _, val in self.__net.state_dict().items()]

    def fit(
        self, parameters: NDArrays, config: Dict[str, Scalar]
    ) -> Tuple[NDArrays, int, Dict[str, Scalar]]:

        secret_id = config[MODEL_ID_CONFIG_KEY]

        log(
            DEBUG,
            "Loading model parameters from MPC secret with identifier '%s'",
            secret_id,
        )
        self.__net.load(uuid.UUID(secret_id))

        log(DEBUG, "Performing training on local dataset")
        # TODO Make number of epochs configurable
        self.train(epochs=1)

        log(DEBUG, "Storing updated model in MPC backend")
        secret_id = self.__net.store()

        log(
            DEBUG,
            "Model parameters stored in MPC secret with identifier '%s'",
            secret_id,
        )

        return (
            self.get_parameters(config={}),
            len(self.__train_loader.dataset),
            {MODEL_ID_CONFIG_KEY: str(secret_id)},
        )

    def evaluate(
        self, parameters: NDArrays, config: Dict[str, Scalar]
    ) -> Tuple[float, int, Dict[str, Scalar]]:

        secret_id = config[MODEL_ID_CONFIG_KEY]

        log(
            DEBUG,
            "Loading model parameters from MPC secret with identifier '%s' for evaluation",
            secret_id,
        )
        self.__net.load(uuid.UUID(secret_id))

        log(DEBUG, "Evaluating the model")
        loss, accuracy = self.test()
        log(DEBUG, "Achieved Loss: %s - Accuracy: %s", loss, accuracy)

        return loss, len(self.__test_loader.dataset), {"accuracy": accuracy}
