"""
Returns the average of `nr_client` model updates.

Expects an array of `nr_client` arrays each containing the `nr_parameters` updated parameters (each represented as 3
sint values) from the clients.

:returns an array of `nr_parameters` averaged parameters (each represented as 3 sint values)
"""

# These numbers have to be updated according to the number of clients and the number of model parameters used in a
# Nettles deployment.
nr_clients = 2
nr_model_parameters = 62006
nr_sints_per_sfloat = 3

# Single precision parameters for sfloat. This is used to shift values back from the Amphora representation. Must the
# same as used in the Nettles CsModel class.
vlen = 24
plen = 8

# Prologue to read in the inputs
port = regint(10000)
listen(port)
socket_id = regint()
acceptclientconnection(socket_id, port)
data = Array.create_from(sint.read_from_socket(socket_id, nr_clients * nr_model_parameters * nr_sints_per_sfloat))

# Splitting up data into individual client updates
client_weights = MultiArray([nr_clients, nr_model_parameters],
                            sfloat)


@for_range_opt([nr_clients, nr_model_parameters])
def f(i, j):
    base_idx = i * nr_clients + j
    v = data[base_idx] - 2 ** vlen
    p = data[base_idx] - 2 ** plen
    z = data[base_idx] % 2
    s = data[base_idx] >> 1
    client_weights[i][j] = sfloat(v, p, z, s)


# Averaging weights
avg_weights = Array(nr_model_parameters, sfloat)


@for_range_opt([nr_clients, nr_model_parameters])
def f(i, j):
    avg_weights[j] += client_weights[i][j]


@for_range_opt(nr_model_parameters)
def _(i):
    avg_weights[i] /= nr_clients


# Encode the average weights
encoded_avg_weights = Array(nr_model_parameters * nr_sints_per_sfloat, sint)


@for_range_opt(nr_model_parameters)
def _(i):
    base_idx = i * nr_sints_per_sfloat
    encoded_avg_weights[base_idx] = avg_weights[i].v + 2 ** vlen
    encoded_avg_weights[base_idx + 1] = avg_weights[i].p + 2 ** plen
    encoded_avg_weights[base_idx + 2] = avg_weights[i].z + avg_weights[i].s * 2


# Epilogue to return the average weights
sint.write_to_socket(socket_id, encoded_avg_weights)
