from collections import OrderedDict

import flwr as fl
import torch

from orchestrator.cs_strategy import MODEL_ID_CONFIG_KEY

class NettleClient(fl.client.NumPyClient):
    def __init__(self, device, cs_net, trainloader, testloader):
        self.device = device
        self.net = cs_net
        self.trainloader = trainloader
        self.testloader = testloader

    def train(epochs):
        criterion = torch.nn.CrossEntropyLoss()
        optimizer = torch.optim.SGD(net.parameters(), lr=0.001, momentum=0.9)
        for _ in range(epochs):
            for images, labels in tqdm(self.trainloader):
                optimizer.zero_grad()
                criterion(self.net(images.to(device)), labels.to(device)).backward()
                optimizer.step()

    def test():
        criterion = torch.nn.CrossEntropyLoss()
        correct, total, loss = 0, 0, 0.0
        with torch.no_grad():
            for images, labels in tqdm(testloader):
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
        self.net.load(secret_id)
        self.train(epochs=1)
        secret_id = self.net.store()
        return self.get_parameters(config={}), len(trainloader.dataset), {MODEL_ID_CONFIG_KEY: secret_id}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        loss, accuracy = self.test(self.net, testloader)
        return loss, len(testloader.dataset), {"accuracy": accuracy}
