"""
CarbyneStack CLI (https://github.com/carbynestack/cli) proxy

example usage:

cli = CLI(
    prime="198766463529478683931867765928436695041",
    r="141515903391459779531506841503331516415",
    r_inv="133854242216446749056083838363708373830",
    providers=[
        Provider(base_url="http://apollo.bocse.carbynestack.io/"),
        Provider(base_url="http://starbuck.bocse.carbynestack.io/")
    ])

secret_id = cli.create_secret(tags={"message":"howdy", "type":"magic"}, values=[5, 15, 25]);
print(secret_id)
print(cli.get_secret(secret_id))
"""

from python_on_whales import docker

class CLI:
    def __init__(self, prime, r, r_inv, providers):
        self.prime = prime
        self.r = r
        self.r_inv = r_inv
        self.providers = providers

    def get_envs(self) -> dict:
        envs = {
            "CS_PRIME": self.prime,
            "CS_R": self.r,
            "CS_R_INV": self.r_inv,
            'CS_NO_SSL_VALIDATION': 'true'
        }

        for i, provider in enumerate(self.providers):
            envs["CS_VCP_{0}_BASE_URL".format(i + 1)] = provider.base_url
            envs["CS_VCP_{0}_AMPHORA_URL".format(i + 1)] = provider.base_url + "amphora"
            envs["CS_VCP_{0}_CASTOR_URL".format(i + 1)] = provider.base_url + "castor"
            envs["CS_VCP_{0}_EPHEMERAL_URL".format(i + 1)] = provider.base_url

        return envs;

    def create_secret(self, tags: dict, values: list) -> str:
        return docker.run("carbynestack/cs-jar", ["amphora", "create-secret"] + map_tags(tags) + list(map(str, values)), envs=self.get_envs())

    def get_secret(self, identifier) -> str:
        return docker.run("carbynestack/cs-jar", ["amphora", "get-secret", identifier], envs=self.get_envs())

    def execute(self, inputs: list, application_name: str, timeout: int = 10) -> str:
        return docker.run("carbynestack/cs-jar", ["ephemeral", "execute", "--timeout", str(timeout)] + map_inputs(inputs) + [application_name], envs=self.get_envs())

def map_tags(tags: dict) -> list:
    tag_arguments = []
    for tag_key in tags:
        tag_arguments.append("--tag")
        tag_arguments.append("{0}={1}".format(tag_key, tags[tag_key]))
    return tag_arguments

def map_inputs(inputs: list) -> list:
    input_arguments = []
    for input_value in inputs:
        input_arguments.append("--input")
        input_arguments.append(input_value)
    return input_arguments

class Provider:
    def __init__(self, base_url):
        self.base_url = base_url
