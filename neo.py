
import ctypes
from ctypes import wintypes

VID = "VID_0FD9"
PID = "PID_009A"

# API nativa do Windows
setupapi = ctypes.WinDLL("setupapi", use_last_error=True)

DIGCF_PRESENT = 0x02
DIGCF_ALLCLASSES = 0x04

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", ctypes.c_byte * 16),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.c_size_t),
    ]

setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiGetClassDevsW.argtypes = [
    ctypes.c_void_p,
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    wintypes.DWORD,
]

setupapi.SetupDiEnumDeviceInfo.restype = wintypes.BOOL
setupapi.SetupDiEnumDeviceInfo.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(SP_DEVINFO_DATA),
]

setupapi.SetupDiGetDeviceInstanceIdW.restype = wintypes.BOOL
setupapi.SetupDiGetDeviceInstanceIdW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(SP_DEVINFO_DATA),
    wintypes.LPWSTR,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

setupapi.SetupDiDestroyDeviceInfoList.argtypes = [
    ctypes.c_void_p
]

handle = setupapi.SetupDiGetClassDevsW(
    None, None, None,
    DIGCF_PRESENT | DIGCF_ALLCLASSES
)

invalid = ctypes.c_void_p(-1).value

if handle == invalid:
    raise ctypes.WinError(ctypes.get_last_error())

found = False

try:
    index = 0

    while True:
        info = SP_DEVINFO_DATA()
        info.cbSize = ctypes.sizeof(info)

        if not setupapi.SetupDiEnumDeviceInfo(
            handle, index, ctypes.byref(info)
        ):
            break

        buffer = ctypes.create_unicode_buffer(1024)

        if setupapi.SetupDiGetDeviceInstanceIdW(
            handle, ctypes.byref(info),
            buffer, len(buffer), None
        ):
            device_id = buffer.value.upper()

            if VID in device_id and PID in device_id:
                print("Stream Deck Neo encontrado!")
                print("ID:", device_id)
                found = True

        index += 1

finally:
    setupapi.SetupDiDestroyDeviceInfoList(handle)

if not found:
    print("Stream Deck Neo não encontrado.")
