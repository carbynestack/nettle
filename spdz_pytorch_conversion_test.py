import unittest

import torch

from utils import spdz_pytorch_conversion as conv


class TestRoundtripConversion(unittest.TestCase):
    def test_rountrip(self):
        """
        Test to verify that a roundtrip conversion from a Pytorch tensor to MP-SPDZ array and back yields the initial tensor.
        """
        tensor = torch.tensor([[4.2434], [1.3243]])
        sfloatArr = conv.float32_tensor_to_sfloat_array(tensor)
        result = conv.sfloat_array_to_float32_tensor(sfloatArr, tensor.shape)
        self.assertTrue(torch.equal(tensor, result), tensor)


if __name__ == '__main__':
    unittest.main()
