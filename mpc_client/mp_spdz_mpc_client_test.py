#
# Copyright (c) 2023 - for information on the respective copyright owner
# see the NOTICE file and/or the repository https://github.com/carbynestack/nettle.
#
# SPDX-License-Identifier: Apache-2.0
#

import tempfile
import unittest
from pathlib import Path

from mpc_client.mp_spdz_mpc_client import MpSpdzMpcClient


class TestMpSpdzMpcClient(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.client = MpSpdzMpcClient(Path(self.tmp_dir.name))

    def tearDown(self):
        pass
        # self.tmp_dir.cleanup()

    def test_store_and_get_secret(self):
        value = [1]
        secret_id = self.client.create_secret(value)
        restored_value = self.client.get_secret(secret_id)[0]
        self.assertEqual(
            value, restored_value, "original and reconstructed values must be the same"
        )

    def test_add_secrets(self):
        self.client.add_program("mp_spdz_mpc_client_test_add.mpc")
        input_a_id = self.client.create_secret([1])
        input_b_id = self.client.create_secret([2])
        result_id = self.client.execute(
            [input_a_id, input_b_id], "mp_spdz_mpc_client_test_add"
        )
        output = self.client.get_secret(result_id)
        self.assertEqual(
            3,
            output[0][0],
            "adding secrets with values 1 and 2 must result in secret with value 3",
        )

    def test_array_output(self):
        self.client.add_program("mp_spdz_mpc_client_test_array_output.mpc")
        result_id = self.client.execute([], "mp_spdz_mpc_client_test_array_output")
        output = self.client.get_secret(result_id)
        self.assertEqual([1, 2], output[0], "array output must be returned correctly")


if __name__ == "__main__":
    unittest.main()
