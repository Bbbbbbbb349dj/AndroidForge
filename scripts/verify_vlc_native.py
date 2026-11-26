"""Validate embedded VLC presence and ELF page alignment, independently of ZIP alignment."""
import struct
import sys
import zipfile


def verify_elf(data: bytes, name: str) -> None:
    if data[:6] != b"\x7fELF\x02\x01":
        raise ValueError(f"{name}: expected little-endian ELF64 ARM64 library")
    phoff = struct.unpack_from("<Q", data, 32)[0]
    entsize, count = struct.unpack_from("<HH", data, 54)
    loads = 0
    for index in range(count):
        offset = phoff + index * entsize
        if struct.unpack_from("<I", data, offset)[0] != 1:
            continue
        loads += 1
        fileoff, vaddr = struct.unpack_from("<QQ", data, offset + 8)
        alignment = struct.unpack_from("<Q", data, offset + 48)[0]
        if alignment < 16384 or fileoff % 16384 != vaddr % 16384:
            raise ValueError(f"{name}: PT_LOAD is not 16 KB page compatible (align={alignment})")
    if not loads:
        raise ValueError(f"{name}: no PT_LOAD segments found")


def verify_apk(path: str) -> None:
    with zipfile.ZipFile(path) as apk:
        for library in ("libvlc.so", "libvlcjni.so"):
            name = f"lib/arm64-v8a/{library}"
            verify_elf(apk.read(name), name)
            print(f"Embedded {name}: ELF 16 KB alignment PASS")


if __name__ == "__main__":
    verify_apk(sys.argv[1])
