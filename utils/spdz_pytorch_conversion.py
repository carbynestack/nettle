import math
import torch

# Single precision parameters for sfloat
vlen = 24
plen = 8


# Converts a Python float into a MP-SPDZ sfloat.
#
# Taken from the MP-SPDZ codebase with return type changed to array.
def float_to_sfloat(v):
    if v < 0:
        s = 1
    else:
        s = 0
    if v == 0:
        v = 0
        p = 0
        z = 1
    else:
        p = int(math.floor(math.log(abs(v), 2))) - vlen + 1
        vv = v
        v = int(round(abs(v) * 2 ** (-p)))
        if v == 2 ** vlen:
            p += 1
            v //= 2
        z = 0
        if p < -2 ** (plen - 1):
            print('Warning: %e truncated to zero' % vv)
            v, p, z = 0, 0, 1
        if p >= 2 ** (plen - 1):
            raise Exception('Cannot convert %s to float with %d exponent bits' % (vv, plen))
    return [v, p, z, s]


# Converts a torch.float32 tensor into an array of MP-SPDZ sfloats.
def float32_tensor_to_sfloat_array(tensor):
    assert tensor.dtype == torch.float32
    f = torch.flatten(tensor)
    sfloats = []
    for _, f in enumerate(f):
        sfloats.append(float_to_sfloat(f.item()))
    return sfloats


# Converts a MP-SPDZ sfloat to a Python float.
def sfloat_to_float(v, p, z, s):
    return (1-2*s)*(1-z)*v*math.pow(2, p)


# Converts an array of MP-SPDZ sfloats into a float32 tensor of the given shape.
def sfloat_array_to_float32_tensor(values, shape):
    tv = []
    for v in values:
        tv.append(sfloat_to_float(*v))
    return torch.reshape(torch.tensor(tv), shape)
