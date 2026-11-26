import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_vlc_native import verify_elf


class VlcElfTest(unittest.TestCase):
    def elf(self, alignment):
        data = bytearray(128)
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<Q", data, 32, 64)
        struct.pack_into("<HH", data, 54, 56, 1)
        struct.pack_into("<I", data, 64, 1)
        struct.pack_into("<Q", data, 112, alignment)
        return data

    def test_accepts_16k_and_larger(self):
        for alignment in (16384, 65536):
            verify_elf(self.elf(alignment), "libvlc.so")

    def test_rejects_4k_or_non_elf(self):
        for data in (self.elf(4096), bytes(128)):
            with self.assertRaises(ValueError):
                verify_elf(data, "libvlc.so")
