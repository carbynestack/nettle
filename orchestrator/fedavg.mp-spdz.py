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

# We used the sfloat encoding that packs the sign and zero bits into a single sint
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
def _(c, mp):
    base_idx = c * nr_model_parameters + mp
    v = data[base_idx] - 2 ** vlen
    p = data[base_idx] - 2 ** plen
    z = data[base_idx] % 2
    s = data[base_idx] >> 1
    client_weights[c][mp] = sfloat(v, p, z, s)


# Averaging weights
avg_weights = Array(nr_model_parameters, sfloat)


@for_range_opt([nr_clients, nr_model_parameters])
def _(c, p):
    avg_weights[p] += client_weights[c][p]


@for_range_opt(nr_model_parameters)
def _(p):
    avg_weights[p] /= nr_clients


# Encode the average weights
encoded_avg_weights = Array(nr_model_parameters * nr_sints_per_sfloat, sint)


@for_range_opt(nr_model_parameters)
def _(p):
    base_idx = p * nr_sints_per_sfloat
    encoded_avg_weights[base_idx] = avg_weights[p].v + 2 ** vlen
    encoded_avg_weights[base_idx + 1] = avg_weights[p].p + 2 ** plen
    encoded_avg_weights[base_idx + 2] = avg_weights[p].z + avg_weights[p].s * 2


# Epilogue to return the average weights
sint.write_to_socket(socket_id, encoded_avg_weights)
