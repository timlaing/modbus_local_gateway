```Salda RIS ModBus test suite```
import struct
import subprocess
import sys

HOST = "192.168.88.254"
PORT = 502
UNIT = 1


def _exchange(adu: bytes) -> bytes:
    esc = "".join(f"\\x{b:02x}" for b in adu)
    script = f"{{ printf '%b' '{esc}'; sleep 0.8; }} | nc -w 3 {HOST} {PORT}"
    return subprocess.run(["sh", "-c", script], capture_output=True).stdout


def read(func: int, address: int, count: int) -> list[int]:
    pdu = struct.pack(">BHH", func, address, count)
    resp = _exchange(struct.pack(">HHHB", 1, 0, len(pdu) + 1, UNIT) + pdu)
    if len(resp) < 9 or resp[7] & 0x80:
        raise RuntimeError(f"bad response: {resp!r}")
    bc = resp[8]
    data = resp[9:9 + bc]
    return [struct.unpack(">H", data[i:i + 2])[0] for i in range(0, len(data), 2)]


def signed(v: int) -> int:
    return v - 0x10000 if v >= 0x8000 else v


def main() -> int:
    modes = {0: "Stand-by", 1: "Building protection",
             2: "Economy", 3: "Comfort", 4: "Emergency"}
    hr = read(0x03, 0, 2)
    print(f"Fan speed / mode (HR0): {hr[0]} ({modes.get(hr[0], '?')})")
    print(f"Set temperature (HR1) : {hr[1]} °C")

    ir = read(0x04, 0, 16)
    print(f"Current mode (IR14)   : {ir[14]} ({modes.get(ir[14], '?')})")
    print(f"Current air flow (IR15): {ir[15]} %")
    print(f"Inside temp (IR6)     : {signed(ir[6]) * 0.1:.1f} °C")
    print(f"Supply temp (IR3)     : {signed(ir[3]) * 0.1:.1f} °C")
    print(f"Exhaust temp (IR0)    : {signed(ir[0]) * 0.1:.1f} °C")
    print(f"Outside temp (IR9)    : {signed(ir[9]) * 0.1:.1f} °C")
    return 0


if __name__ == "__main__":
    sys.exit(main())
