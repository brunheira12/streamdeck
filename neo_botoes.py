
import ctypes as C
from ctypes import wintypes as W
from neo_logs import configurar_logs, descrever_acao, registrar_botao, executar_acao as executar_acao_log, iniciar

logger = configurar_logs(__name__ if __name__ != "__main__" else "neo_botoes")
from neo_hid import ler_relatorios

# ==================================================
# CONFIGURACOES
# ==================================================

VID = "vid_0fd9"
PID = "pid_009a"

# Acoes executadas ao pressionar cada tecla
ACOES = {
    1: ["notepad.exe"],
    2: ["calc.exe"],
    # 3: ["mspaint.exe"],
    # 4: ["explorer.exe"],
}

INVALID_HANDLE = C.c_void_p(-1).value
ERROR_NO_MORE_ITEMS = 259

# ==================================================
# DLLs NATIVAS DO WINDOWS
# ==================================================

setup = C.WinDLL("setupapi", use_last_error=True)
hid = C.WinDLL("hid", use_last_error=True)
kernel = C.WinDLL("kernel32", use_last_error=True)


# ==================================================
# ESTRUTURAS WINDOWS / HID
# ==================================================

class GUID(C.Structure):
    _fields_ = [
        ("Data1", W.DWORD),
        ("Data2", W.WORD),
        ("Data3", W.WORD),
        ("Data4", C.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(C.Structure):
    _fields_ = [
        ("cbSize", W.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", W.DWORD),
        ("Reserved", C.c_size_t),
    ]


class HIDP_CAPS(C.Structure):
    _fields_ = [
        ("Usage", W.USHORT),
        ("UsagePage", W.USHORT),
        ("InputReportByteLength", W.USHORT),
        ("OutputReportByteLength", W.USHORT),
        ("FeatureReportByteLength", W.USHORT),
        ("Reserved", W.USHORT * 17),
        ("NumberLinkCollectionNodes", W.USHORT),
        ("NumberInputButtonCaps", W.USHORT),
        ("NumberInputValueCaps", W.USHORT),
        ("NumberInputDataIndices", W.USHORT),
        ("NumberOutputButtonCaps", W.USHORT),
        ("NumberOutputValueCaps", W.USHORT),
        ("NumberOutputDataIndices", W.USHORT),
        ("NumberFeatureButtonCaps", W.USHORT),
        ("NumberFeatureValueCaps", W.USHORT),
        ("NumberFeatureDataIndices", W.USHORT),
    ]


# ==================================================
# ASSINATURAS DAS FUNCOES NATIVAS
# ==================================================

hid.HidD_GetHidGuid.argtypes = [C.POINTER(GUID)]
hid.HidD_GetHidGuid.restype = None

hid.HidD_GetPreparsedData.argtypes = [
    W.HANDLE,
    C.POINTER(C.c_void_p),
]
hid.HidD_GetPreparsedData.restype = W.BOOL

hid.HidD_FreePreparsedData.argtypes = [C.c_void_p]
hid.HidD_FreePreparsedData.restype = W.BOOL

hid.HidP_GetCaps.argtypes = [
    C.c_void_p,
    C.POINTER(HIDP_CAPS),
]
hid.HidP_GetCaps.restype = C.c_long

setup.SetupDiGetClassDevsW.argtypes = [
    C.POINTER(GUID),
    W.LPCWSTR,
    W.HWND,
    W.DWORD,
]
setup.SetupDiGetClassDevsW.restype = W.HANDLE

setup.SetupDiEnumDeviceInterfaces.argtypes = [
    W.HANDLE,
    C.c_void_p,
    C.POINTER(GUID),
    W.DWORD,
    C.POINTER(SP_DEVICE_INTERFACE_DATA),
]
setup.SetupDiEnumDeviceInterfaces.restype = W.BOOL

setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    W.HANDLE,
    C.POINTER(SP_DEVICE_INTERFACE_DATA),
    C.c_void_p,
    W.DWORD,
    C.POINTER(W.DWORD),
    C.c_void_p,
]
setup.SetupDiGetDeviceInterfaceDetailW.restype = W.BOOL

setup.SetupDiDestroyDeviceInfoList.argtypes = [W.HANDLE]
setup.SetupDiDestroyDeviceInfoList.restype = W.BOOL

kernel.CreateFileW.argtypes = [
    W.LPCWSTR,
    W.DWORD,
    W.DWORD,
    C.c_void_p,
    W.DWORD,
    W.DWORD,
    W.HANDLE,
]
kernel.CreateFileW.restype = W.HANDLE

kernel.ReadFile.argtypes = [
    W.HANDLE,
    C.c_void_p,
    W.DWORD,
    C.POINTER(W.DWORD),
    C.c_void_p,
]
kernel.ReadFile.restype = W.BOOL

kernel.CloseHandle.argtypes = [W.HANDLE]
kernel.CloseHandle.restype = W.BOOL


# ==================================================
# ACOES DOS BOTOES
# ==================================================

def executar_acao(numero):
    executar_acao_log(logger, ACOES, numero)


# ==================================================
# LOCALIZAR STREAM DECK NEO
# ==================================================

def encontrar_neo():
    guid = GUID()
    hid.HidD_GetHidGuid(C.byref(guid))

    devices = setup.SetupDiGetClassDevsW(
        C.byref(guid),
        None,
        None,
        0x12,
    )

    if devices == INVALID_HANDLE:
        raise C.WinError(C.get_last_error())

    try:
        index = 0

        while True:
            info = SP_DEVICE_INTERFACE_DATA()
            info.cbSize = C.sizeof(info)

            ok = setup.SetupDiEnumDeviceInterfaces(
                devices,
                None,
                C.byref(guid),
                index,
                C.byref(info),
            )

            if not ok:
                error = C.get_last_error()

                if error == ERROR_NO_MORE_ITEMS:
                    break

                raise C.WinError(error)

            index += 1

            needed = W.DWORD()

            setup.SetupDiGetDeviceInterfaceDetailW(
                devices,
                C.byref(info),
                None,
                0,
                C.byref(needed),
                None,
            )

            if not needed.value:
                continue

            buffer = C.create_string_buffer(needed.value)

            cb_size = (
                8 if C.sizeof(C.c_void_p) == 8 else 6
            )

            C.cast(
                buffer,
                C.POINTER(W.DWORD)
            ).contents.value = cb_size

            ok = setup.SetupDiGetDeviceInterfaceDetailW(
                devices,
                C.byref(info),
                buffer,
                needed.value,
                C.byref(needed),
                None,
            )

            if not ok:
                continue

            path = C.wstring_at(
                C.addressof(buffer) + 4
            )

            if VID not in path.lower():
                continue

            if PID not in path.lower():
                continue

            logger.info('Interface encontrada:')
            logger.info(str(path))

            handle = kernel.CreateFileW(
                path,
                0x80000000,
                0x03,
                None,
                3,
                0,
                None,
            )

            if handle != INVALID_HANDLE:
                return handle

            logger.warning('%s %s', 'Falha ao abrir:', C.get_last_error())

    finally:
        setup.SetupDiDestroyDeviceInfoList(devices)

    raise RuntimeError(
        "Nao foi possivel abrir o Stream Deck Neo."
    )


# ==================================================
# CONSULTAR CAPACIDADES HID
# ==================================================

def consultar_capacidades(handle):
    preparsed = C.c_void_p()

    if not hid.HidD_GetPreparsedData(
        handle,
        C.byref(preparsed),
    ):
        raise C.WinError(C.get_last_error())

    try:
        caps = HIDP_CAPS()

        status = hid.HidP_GetCaps(
            preparsed,
            C.byref(caps),
        )

        if status < 0:
            raise RuntimeError(
                f"HidP_GetCaps falhou: {status:#x}"
            )

        logger.info('=== Capacidades HID ===')
        logger.info('%s %s %s', 'Input:', caps.InputReportByteLength, 'bytes')
        logger.info('%s %s %s', 'Output:', caps.OutputReportByteLength, 'bytes')
        logger.info('%s %s %s', 'Feature:', caps.FeatureReportByteLength, 'bytes')

        return caps.InputReportByteLength

    finally:
        hid.HidD_FreePreparsedData(preparsed)


# ==================================================
# MONITORAR BOTOES
# ==================================================

def monitorar_botoes(handle, report_size):
    if report_size <= 0:
        raise RuntimeError(
            "Tamanho de Input Report invalido."
        )

    logger.info('Stream Deck Neo conectado!')
    logger.info('Pressione os botoes.')
    logger.info('Ctrl+C para encerrar.')

    # O primeiro relatorio pode chegar somente quando uma tecla e pressionada.
    previous = [0] * 10

    with ler_relatorios(kernel, handle, report_size) as relatorios:
        for data in relatorios:

            if not data:
                continue

            if data[0] != 0x01 or len(data) < 14:
                logger.warning('%s %s', 'Relatorio desconhecido:', data.hex(' '))
                continue

            states = list(data[4:14])

            for i, state in enumerate(states):
                if state == previous[i]:
                    continue

                registrar_botao(logger, ACOES, i, state)

                # Executar apenas ao pressionar
                if state and i < 8:
                    executar_acao(i + 1)

            previous = states


# ==================================================
# MAIN
# ==================================================

def main():
    for numero, comando in ACOES.items():
        logger.info('evento=configuracao | botao=Tecla %s | acao=%s', numero, descrever_acao(comando))
    logger.info('evento=conexao_iniciada | Procurando Stream Deck Neo')
    handle = encontrar_neo()
    logger.info('evento=conectado | Stream Deck Neo conectado')

    try:
        report_size = consultar_capacidades(handle)

        monitorar_botoes(
            handle,
            report_size
        )

    finally:
        kernel.CloseHandle(handle)
        logger.info('evento=desconectado | Conexao encerrada')


if __name__ == '__main__':
    raise SystemExit(iniciar(logger, main))
