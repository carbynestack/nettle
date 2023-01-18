import docker
import ast

from typing import Dict, List, Tuple

from docker.errors import DockerException


class CLI:
    """
    A CLI proxy that invokes the CarbyneStack CLI (https://github.com/carbynestack/cli) running via a docker container.

    Please ensure you build the docker container locally via `make build` on the root directory.

    Attributes
    ----------
    prime : int
        Modulus N as used by the MPC backend
    r : int
        Auxiliary modulus R as used by the MPC backend
    r_inv : int
        Multiplicative inverse for the auxiliary modulus R as used by the MPC backend
    providers : list
        A list of CarbyneStack providers that will perform the

    Methods
    -------
    colorspace(c='rgb')
        Represent the photo in the given colorspace.
    gamma(n=1.0)
        Change the photo's gamma exposure.

    Raises
    ------
    CLIException
        If Docker is not running or there was an issue connecting to it
    """

    def __init__(self, prime: int, r: int, r_inv: int, providers: List["Provider"]):
        self.prime = prime
        self.r = r
        self.r_inv = r_inv
        self.providers = providers
        try:
            self.docker_client = docker.APIClient()
        except DockerException as docker_exception:
            raise CLIException(message=str(docker_exception))

    def create_secret(self, values: List[int], tags: Dict[str, str] = None) -> str:
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
        CLIException
            You haven't built the docker image via `make build` or the CLI raised an exception
        """
        (status_code, stdout, stderr) = self.__run_container(
            entrypoint=["java", "-jar", "cs.jar", "amphora", "create-secret"] + self.__map_tags(tags),
            stdin_open=True,
            stdin_value='\n'.join(map(str, values)))

        if status_code == 1:
            raise CLIException(message=stderr)
        else:
            return str(stdout).splitlines()[1]

    def get_secret(self, identifier: str) -> Tuple[List[int], Dict[str, str]]:
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
        CLIException
            You haven't built the docker image via `make build` or the CLI raised an exception
        """
        (status_code, stdout, stderr) = self.__run_container(
            entrypoint=["java", "-jar", "cs.jar", "amphora", "get-secret", identifier])

        if status_code == 1:
            raise CLIException(message=stderr)
        else:
            result_lines = stdout.splitlines()
            tags = {}
            if len(result_lines) > 1:
                for line_number in range(1, len(result_lines)):
                    split_line = result_lines[line_number].split("->")
                    tags[split_line[0].strip()] = split_line[1].strip()

            return ast.literal_eval(result_lines[0]), tags

    def execute(self, inputs: List[str], application_name: str, timeout: int = 10) -> str:
        """
        Invokes an Ephemeral function with the given inputs secrets.

        Parameters
        ----------

        inputs: list, required
            A list of secret IDs (UUID) that will be used in the mpc program

        application_name : str, required
            The mpc application name, which should be pre-packaged with the serverless ephemeral image

        timeout: int, optional
            Maximum time allowed for the request in seconds.  Default 10(s)

        Returns
        -------
        str
            The secret ID in UUID format

        Raises
        ------
        CLIException
            You haven't built the docker image via `make build` or the CLI raised an exception
        """

        (status_code, stdout, stderr) = self.__run_container(
            entrypoint=["ephemeral", "execute", "--timeout", str(timeout)] + self.__map_inputs(inputs) + [application_name])

        if status_code == 1:
            raise CLIException(message=stderr)
        else:
            return stdout

    def __run_container(self, entrypoint: List[str], stdin_open=False, stdin_value="") -> Tuple[int, str, str]:
        """
        Runs the CarbyneStack CLI docker image

        Parameters
        ----------

        entrypoint: list, required
            A list of arguments
            Example: ["java", "-jar", "cs.jar", "amphora", "get-secret", identifier]

        stdin_open : bool, optional
            Open the STDIN to allow data to be passed (required for large arrays of secrets)

        stdin_value: str, optional
            The str that will be passed into the docker container via STDIN

        Returns
        -------
        tuple
            A tuple of:
                1. Docker Container's Status Code
                2. the STDOUT of the container
                3. the STDERR of the container
        """

        container = self.docker_client.create_container(
            'carbynestack/cs-jar',
            stdin_open=stdin_open,
            environment=self.__get_envs(),
            entrypoint=entrypoint,
        )

        if stdin_open:
            sock = self.docker_client.attach_socket(
                container,
                params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1})
            self.docker_client.start(container)
            sock._sock.send(str.encode(stdin_value))
            sock._sock.close()
            sock.close()

        self.docker_client.start(container)

        status = self.docker_client.wait(container)
        status_code = status["StatusCode"]
        stdout = self.docker_client.logs(container, stderr=False).decode()
        stderr = self.docker_client.logs(container, stdout=False).decode()

        self.docker_client.remove_container(container)

        return status_code, str(stdout), str(stderr)

    def __get_envs(self) -> Dict[str, str]:
        """
        build the dict of CarbyneStack CLI configuration environment variables

        see: https://github.com/carbynestack/cli#configuration

        Returns
        -------
        dict
            Environment variables for the CarbyneStack CLI
        """
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

        return envs

    @staticmethod
    def __map_tags(tags: Dict[str,str] = None) -> List[str]:
        """
        Maps the passed in dict of tags to a list of arguments used in docker run

        Parameters
        ----------

        tags: dict, required
            A list of secret IDs (UUID) that will be used in the mpc program.
            Example: {"message":"howdy", "type":"magic"}

        Returns
        -------
        list
            A list of tag arguments for docker run
            Example: ["--tag", "message=howdy", "--tag", "type=magic"]
        """

        if tags is None:
            return []

        tag_arguments = []
        for tag_key in tags:
            tag_arguments.append("--tag")
            tag_arguments.append("{0}={1}".format(tag_key, tags[tag_key]))
        return tag_arguments

    @staticmethod
    def __map_inputs(inputs: List[str]) -> List[str]:
        """
        Maps the passed in list of input ids to a list of arguments used in docker run

        Parameters
        ----------

        inputs: list, required
            A list of secret IDs (UUID) that will be used in the mpc program.
            Example: ["91163E6B-AD8E-42EE-8374-5C471B5D97B5", "D97ACC22-1D5A-442C-8A52-0D26EDC55C11"]

        Returns
        -------
        list
            A list of tag arguments for docker run
            Example: ["--input", "91163E6B-AD8E-42EE-8374-5C471B5D97B5", "--input", "D97ACC22-1D5A-442C-8A52-0D26EDC55C11"]
        """
        input_arguments = []
        for input_value in inputs:
            input_arguments.append("--input")
            input_arguments.append(input_value)
        return input_arguments


class Provider:
    """
    CarbyneStack Provider

    Attributes
    ----------
    base_url : str
       The base URL of a CarbyneStack provider that all other connection params derive from
       Example: "https://apollo.bocse.carbynestack.io/"
    """

    def __init__(self, base_url: str):
        self.base_url = base_url

class CLIException(Exception):
    """Exception raised while communicating with the CarbyneStack CLI.

    Attributes
    ----------
    message : str, required
        explanation of the error
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)