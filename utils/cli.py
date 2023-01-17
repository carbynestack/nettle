import docker
import ast

class CLI:
    """
    Array with associated photographic information.

    Attributes
    ----------
    prime : int
        Modulus N as used by the MPC backend
    r : int
        Auxiliary modulus R as used by the MPC backend
    r_inv : int
        Multiplicative inverse for the auxiliary modulus R as used by the MPC backend
    providers : list

    Methods
    -------
    colorspace(c='rgb')
        Represent the photo in the given colorspace.
    gamma(n=1.0)
        Change the photo's gamma exposure.

    """

    def __init__(self, prime: int, r: int, r_inv: int, providers: list):
        self.prime = prime
        self.r = r
        self.r_inv = r_inv
        self.providers = providers
        self.docker_client = docker.APIClient()

    def get_envs(self) -> dict:
        envs = {
            "CS_PRIME": str(self.prime),
            "CS_R": str(self.r),
            "CS_R_INV": str(self.r_inv),
            'CS_NO_SSL_VALIDATION': 'true'
        }

        for i, provider in enumerate(self.providers):
            envs["CS_VCP_{0}_BASE_URL".format(i + 1)] = provider.base_url
            envs["CS_VCP_{0}_AMPHORA_URL".format(i + 1)] = provider.base_url + "amphora"
            envs["CS_VCP_{0}_CASTOR_URL".format(i + 1)] = provider.base_url + "castor"
            envs["CS_VCP_{0}_EPHEMERAL_URL".format(i + 1)] = provider.base_url

        return envs;

    def create_secret(self, values: list, tags: dict = {}) -> str:
        """
        Secret-shares the passed in values and uploads them to all CarbyneStack Providers.

        Parameters
        ----------
        values : list, required
            A list of integers of arbitrary length.
            Example: [5, 15, 909340340928304820938409284]
        tags : dict, optional
            A dict of tags to assign the secret to in Amphora.
            Example: {"message":"howdy", "type":"magic"}

        Returns
        -------
        id : str
            the secret ID in UUID format

        Raises
        ------
        DockerException
            If Docker is not running or you haven't built the docker image via `make build`
        """
        container = self.docker_client.create_container(
            'carbynestack/cs-jar',
            stdin_open=True,
            environment=self.get_envs(),
            entrypoint=["java", "-jar", "cs.jar", "amphora", "create-secret"] + map_tags(tags),
        )

        sock = self.docker_client.attach_socket(container, params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1})
        self.docker_client.start(container)
        sock._sock.send(str.encode('\n'.join(map(str, values))))
        sock._sock.close()
        sock.close()

        status = self.docker_client.wait(container)
        status_code = status["StatusCode"]
        stdout = self.docker_client.logs(container, stderr=False).decode()
        stderr = self.docker_client.logs(container, stdout=False).decode()

        # TODO: handle status_code & stderr

        self.docker_client.remove_container(container)

        return str(stdout).splitlines()[1]

    def get_secret(self, identifier: str) -> tuple:
        """
        Retrieves the secret from the CarbyneStack providers and recombines the shares into the original value

        Parameters
        ----------
        identifier : string, required
            The UUID of the secret that is stored in CarbyneStack

        Returns
        -------
        tuple
            A tuple containing a list of secret values and a dict of tags
            Example: ([5, 15, 20],{"message":"howdy", "type":"magic", "creation-date", 1673945646375})

        Raises
        ------
        DockerException
            If Docker is not running or you haven't built the docker image via `make build`
        """
        container = self.docker_client.create_container(
            'carbynestack/cs-jar',
            stdin_open=True,
            environment=self.get_envs(),
            entrypoint=["java", "-jar", "cs.jar", "amphora", "get-secret", identifier],
        )

        sock = self.docker_client.attach_socket(container, params={"stdin": 0, "stdout": 1, "stderr": 1, "stream": 1})
        self.docker_client.start(container)

        status = self.docker_client.wait(container)
        status_code = status["StatusCode"]
        stdout = self.docker_client.logs(container, stderr=False).decode()
        stderr = self.docker_client.logs(container, stdout=False).decode()

        # TODO: handle status_code & stderr

        self.docker_client.remove_container(container)

        result_lines = str(stdout).splitlines()
        tags = {}
        if len(result_lines) > 1:
            for line_number in range(1, len(result_lines)):
                split_line = result_lines[line_number].split("->")
                tags[split_line[0].strip()] = split_line[1].strip()

        return ast.literal_eval(result_lines[0]), tags

    def execute(self, inputs: list, application_name: str, timeout: int = 10) -> str:
         docker.run("carbynestack/cs-jar", ["ephemeral", "execute", "--timeout", str(timeout)] + map_inputs(inputs) + [application_name], envs=self.get_envs(), remove=True), None


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
