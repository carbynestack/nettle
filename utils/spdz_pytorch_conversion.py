#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import math

import torch

#: Single precision significant bit-length for MP-SPDZ sfloat
sfloat_significant_bit_length = 24

#: Single precision exponent bit-length for MP-SPDZ sfloat
sfloat_exponent_bit_length = 8


def float_to_sfloat(v):
    """Converts a Python float into an MP-SPDZ sfloat.

    NOTE: This is taken from the MP-SPDZ codebase with return type changed to array.

    :param v: the float to be converted
    :return: 4-element sfloat array
    """
    if v < 0:
        s = 1
    else:
        s = 0
    if v == 0:
        v = 0
        p = 0
        z = 1
    else:
        p = int(math.floor(math.log(abs(v), 2))) - sfloat_significant_bit_length + 1
        vv = v
        v = int(round(abs(v) * 2 ** (-p)))
        if v == 2**sfloat_significant_bit_length:
            p += 1
            v //= 2
        z = 0
        if p < -(2 ** (sfloat_exponent_bit_length - 1)):
            print("Warning: %e truncated to zero" % vv)
            v, p, z = 0, 0, 1
        if p >= 2 ** (sfloat_exponent_bit_length - 1):
            raise Exception(
                "Cannot convert %s to float with %d exponent bits"
                % (vv, sfloat_exponent_bit_length)
            )
    return [v, p, z, s]


def encode_sfloat(v):
    """Encodes a 4-tuple into a 3-tuple sfloat by packing the zero and sign bits into a single element.

    :param v: the 4-element sfloat to encode
    :returns: the 3-element encoded sfloat
    """
    return [v[0], v[1], v[2] + v[3] * 2]


def decode_sfloat(v):
    """Decodes a 3-tuple sfloat generated by encode into a 4-tuple.

    :param v: the 3-element encoded sfloat to decode
    :returns: the 4-element decoded sfloat
    """
    return [v[0], v[1], v[2] % 2, v[2] >> 1]


def float32_tensor_to_sfloat_array(tensor, shift=False):
    """Converts a torch.float32 tensor into an array of encoded MP-SPDZ sfloats.

    :param tensor: the torch.float32 tensor to be converted
    :param shift: if True, 'shifts' sfloat significant and exponent values such that the all of them are positive
    :return: the array of 3-element sfloats
    """
    if tensor.dtype is not torch.float32:
        raise ValueError(
            f"tensor type is not supported {tensor.dtype}; must be {torch.float32}"
        )
    f = torch.flatten(tensor)
    sfloats = []
    for _, f in enumerate(f):
        sfloat = float_to_sfloat(f.item())
        if shift:
            sfloat[0] += 2**sfloat_significant_bit_length
            sfloat[1] += 2**sfloat_exponent_bit_length
        sfloats.append(encode_sfloat(sfloat))
    return sfloats


def sfloat_to_float(v):
    """Converts an MP-SPDZ sfloat to a Python float.

    :param v: the 4-element sfloat to convert
    :return: the float32 equivalent
    """
    return (1 - 2 * v[3]) * (1 - v[2]) * v[0] * math.pow(2, v[1])


# Converts an array of MP-SPDZ sfloats into a float32 tensor of the given shape.
def sfloat_array_to_float32_tensor(values, shape, shift=False):
    """Converts an array of MP-SPDZ sfloats into a float32 tensor of the given shape.

    :param values: the array of 3-element sfloats to be converted
    :param shape: the shape of returned tensor
    :param shift: if True, 'shifts' sfloat significant and exponent values back
                  (see :func:`float32_tensor_to_sfloat_array`)
    :return: the resulting tensor
    """
    tv = []
    for v in values:
        if shift:
            v[0] -= 2**sfloat_significant_bit_length
            v[1] -= 2**sfloat_exponent_bit_length
        tv.append(sfloat_to_float(decode_sfloat(v)))
    return torch.reshape(torch.tensor(tv), shape)
