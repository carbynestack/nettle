from collections import OrderedDict
from logging import DEBUG

import flwr as fl
from flwr.common.logger import log
import torch
from tqdm import tqdm

from orchestrator.cs_strategy import MODEL_ID_CONFIG_KEY


class NettleClient(fl.client.NumPyClient):
    def __init__(self, device, cs_net, trainloader, testloader):
        self.device = device
        self.net = cs_net
        self.trainloader = trainloader
        self.testloader = testloader

    def train(self, epochs):
        criterion = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.SGD(self.net.parameters(), lr=0.001, momentum=0.9)
        for _ in range(epochs):
            for images, labels in tqdm(self.trainloader):
                optimizer.zero_grad()
                criterion(self.net(images.to(self.device)), labels.to(self.device)).backward()
                optimizer.step()

    def test(self):
        criterion = torch.nn.CrossEntropyLoss()
        correct, total, loss = 0, 0, 0.0
        with torch.no_grad():
            for images, labels in tqdm(self.testloader):
                outputs = self.net(images.to(self.device))
                labels = labels.to(self.device)
                loss += criterion(outputs, labels).item()
                total += labels.size(0)
                correct += (torch.max(outputs.data, 1)[1] == labels).sum().item()
        return loss / len(self.testloader.dataset), correct / total

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.net.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(self.net.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v) for k, v in params_dict})
        self.net.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        secret_id = config[MODEL_ID_CONFIG_KEY]
        log(DEBUG, "Loading model %s", secret_id)
        self.net.load(secret_id)
        log(DEBUG, "Train %s", secret_id)
        self.train(epochs=1)
        log(DEBUG, "Storing...")
        secret_id = self.net.store()
        log(DEBUG, "New model amphora sid $s", secret_id)
        return self.get_parameters(config={}), len(self.trainloader.dataset), {MODEL_ID_CONFIG_KEY: secret_id}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        loss, accuracy = self.test()
        return loss, len(self.testloader.dataset), {"accuracy": accuracy}
