#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import unittest

import numpy as np
import torch

from utils import spdz_pytorch_conversion as conv


class TestRoundtripConversion(unittest.TestCase):
    def test_rountrip(self):
        """
        Test to verify that a roundtrip conversion from a Pytorch tensor to MP-SPDZ array and back yields the initial
        tensor.
        """
        tensor = torch.tensor([[4.2434], [1.3243]])
        sfloatArr = conv.float32_tensor_to_sfloat_array(tensor)
        result = conv.sfloat_array_to_float32_tensor(sfloatArr, tensor.shape)
        self.assertTrue(torch.equal(tensor, result), tensor)

    def test_roundtrip_with_negative(self):
        """
        Test to verify that a roundtrip conversion from a Pytorch tensor with negative values to MP-SPDZ array and
        back yields the initial tensor and the that all values sfloat parameters are positive.
        """
        tensor = torch.tensor([[-4.2434], [-1.3243]])
        sfloatArr = conv.float32_tensor_to_sfloat_array(tensor, shift=True)
        for v in sfloatArr:
            for i in v:
                self.assertTrue(np.sign(i) != -1)
        result = conv.sfloat_array_to_float32_tensor(
            sfloatArr, tensor.shape, shift=True
        )
        self.assertTrue(torch.equal(tensor, result), tensor)


if __name__ == "__main__":
    unittest.main()
