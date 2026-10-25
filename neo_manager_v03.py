"""Stream Deck Neo Manager v0.3 - Windows HID; Pillow para o relogio."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
from neo_logs import configurar_logs, descrever_acao, registrar_botao, executar_acao as executar_acao_log, iniciar

logger = configurar_logs(__name__ if __name__ != "__main__" else "neo_manager_v03")
from neo_hid import ler_relatorios
from neo_display import RelogioDisplay
import struct

VID = 'vid_0fd9'
PID = 'pid_009a'
ACOES = {1: ['notepad.exe'], 2: ['calc.exe']}
CORES = [
    (35, 100, 210), (24, 155, 110), (115, 70, 185), (210, 130, 30),
    (175, 55, 80), (30, 135, 155), (95, 110, 130), (70, 70, 70),
]
# Optional: put already-rotated 96x96 JPEGs named tecla1.jpg, ... tecla8.jpg in ./icones
PASTA_ICONES = Path(__file__).resolve().parent / 'icones'
INVALID_HANDLE = C.c_void_p(-1).value
ERROR_NO_MORE_ITEMS = 259
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000

setup = C.WinDLL('setupapi', use_last_error=True)
hid = C.WinDLL('hid', use_last_error=True)
kernel = C.WinDLL('kernel32', use_last_error=True)

class GUID(C.Structure):
    _fields_ = [('Data1', W.DWORD), ('Data2', W.WORD), ('Data3', W.WORD), ('Data4', C.c_ubyte * 8)]

class SP_DEVICE_INTERFACE_DATA(C.Structure):
    _fields_ = [('cbSize', W.DWORD), ('InterfaceClassGuid', GUID), ('Flags', W.DWORD), ('Reserved', C.c_size_t)]

class HIDP_CAPS(C.Structure):
    _fields_ = [('Usage', W.USHORT), ('UsagePage', W.USHORT),
               ('InputReportByteLength', W.USHORT), ('OutputReportByteLength', W.USHORT),
               ('FeatureReportByteLength', W.USHORT), ('Reserved', W.USHORT * 17),
               ('NumberLinkCollectionNodes', W.USHORT), ('NumberInputButtonCaps', W.USHORT),
               ('NumberInputValueCaps', W.USHORT), ('NumberInputDataIndices', W.USHORT),
               ('NumberOutputButtonCaps', W.USHORT), ('NumberOutputValueCaps', W.USHORT),
               ('NumberOutputDataIndices', W.USHORT), ('NumberFeatureButtonCaps', W.USHORT),
               ('NumberFeatureValueCaps', W.USHORT), ('NumberFeatureDataIndices', W.USHORT)]

hid.HidD_GetHidGuid.argtypes = [C.POINTER(GUID)]
hid.HidD_GetHidGuid.restype = None
hid.HidD_GetPreparsedData.argtypes = [W.HANDLE, C.POINTER(C.c_void_p)]
hid.HidD_GetPreparsedData.restype = W.BOOL
hid.HidD_FreePreparsedData.argtypes = [C.c_void_p]
hid.HidD_FreePreparsedData.restype = W.BOOL
hid.HidP_GetCaps.argtypes = [C.c_void_p, C.POINTER(HIDP_CAPS)]
hid.HidP_GetCaps.restype = C.c_long
hid.HidD_SetFeature.argtypes = [W.HANDLE, C.c_void_p, W.ULONG]
hid.HidD_SetFeature.restype = W.BOOL
setup.SetupDiGetClassDevsW.argtypes = [C.POINTER(GUID), W.LPCWSTR, W.HWND, W.DWORD]
setup.SetupDiGetClassDevsW.restype = W.HANDLE
setup.SetupDiEnumDeviceInterfaces.argtypes = [W.HANDLE, C.c_void_p, C.POINTER(GUID), W.DWORD, C.POINTER(SP_DEVICE_INTERFACE_DATA)]
setup.SetupDiEnumDeviceInterfaces.restype = W.BOOL
setup.SetupDiGetDeviceInterfaceDetailW.argtypes = [W.HANDLE, C.POINTER(SP_DEVICE_INTERFACE_DATA), C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]
setup.SetupDiGetDeviceInterfaceDetailW.restype = W.BOOL
setup.SetupDiDestroyDeviceInfoList.argtypes = [W.HANDLE]
setup.SetupDiDestroyDeviceInfoList.restype = W.BOOL
kernel.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, C.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
kernel.CreateFileW.restype = W.HANDLE
kernel.ReadFile.argtypes = [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]
kernel.ReadFile.restype = W.BOOL
kernel.WriteFile.argtypes = [W.HANDLE, C.c_void_p, W.DWORD, C.POINTER(W.DWORD), C.c_void_p]
kernel.WriteFile.restype = W.BOOL
kernel.CloseHandle.argtypes = [W.HANDLE]
kernel.CloseHandle.restype = W.BOOL


def encontrar_neo():
    guid = GUID()
    hid.HidD_GetHidGuid(C.byref(guid))
    devices = setup.SetupDiGetClassDevsW(C.byref(guid), None, None, 0x12)
    if devices == INVALID_HANDLE:
        raise C.WinError(C.get_last_error())
    try:
        index = 0
        while True:
            info = SP_DEVICE_INTERFACE_DATA()
            info.cbSize = C.sizeof(info)
            if not setup.SetupDiEnumDeviceInterfaces(devices, None, C.byref(guid), index, C.byref(info)):
                err = C.get_last_error()
                if err == ERROR_NO_MORE_ITEMS:
                    break
                raise C.WinError(err)
            index += 1
            needed = W.DWORD()
            setup.SetupDiGetDeviceInterfaceDetailW(devices, C.byref(info), None, 0, C.byref(needed), None)
            if not needed.value:
                continue
            detail = C.create_string_buffer(needed.value)
            C.cast(detail, C.POINTER(W.DWORD)).contents.value = 8 if C.sizeof(C.c_void_p) == 8 else 6
            if not setup.SetupDiGetDeviceInterfaceDetailW(devices, C.byref(info), detail, needed.value, C.byref(needed), None):
                continue
            path = C.wstring_at(C.addressof(detail) + 4)
            if VID not in path.lower() or PID not in path.lower():
                continue
            logger.info('%s %s', 'Interface encontrada:', path)
            handle = kernel.CreateFileW(path, GENERIC_READ | GENERIC_WRITE, 3, None, 3, 0, None)
            if handle != INVALID_HANDLE:
                return handle
            logger.warning('%s %s', 'Falha ao abrir interface para leitura/escrita:', C.get_last_error())
    finally:
        setup.SetupDiDestroyDeviceInfoList(devices)
    raise RuntimeError('Nao foi possivel abrir o Neo para leitura e escrita. Feche o software Elgato, se estiver aberto.')


def consultar_capacidades(handle):
    preparsed = C.c_void_p()
    if not hid.HidD_GetPreparsedData(handle, C.byref(preparsed)):
        raise C.WinError(C.get_last_error())
    try:
        caps = HIDP_CAPS()
        status = hid.HidP_GetCaps(preparsed, C.byref(caps))
        if status < 0:
            raise RuntimeError(f'HidP_GetCaps falhou: {status:#x}')
        logger.info(f'Input: {caps.InputReportByteLength} | Output: {caps.OutputReportByteLength} | Feature: {caps.FeatureReportByteLength}')
        return caps
    finally:
        hid.HidD_FreePreparsedData(preparsed)


def set_feature(handle, size, payload):
    if len(payload) > size:
        raise ValueError('Feature report maior que o permitido')
    buf = C.create_string_buffer(payload.ljust(size, b'\x00'), size)
    if not hid.HidD_SetFeature(handle, buf, size):
        raise C.WinError(C.get_last_error())


def pintar_tecla(handle, feature_size, index, rgb):
    # Report ID 03, command 06, zero-based index, R G B
    payload = bytes([0x03, 0x06, index, *rgb])
    set_feature(handle, feature_size, payload)


def enviar_jpeg(handle, output_size, index, jpeg):
    if output_size <= 8:
        raise RuntimeError('Output report pequeno demais')
    capacidade = output_size - 8
    for numero, inicio in enumerate(range(0, len(jpeg), capacidade)):
        bloco = jpeg[inicio:inicio + capacidade]
        ultimo = int(inicio + len(bloco) >= len(jpeg))
        header = bytes([0x02, 0x07, index, ultimo]) + struct.pack('<HH', len(bloco), numero)
        pacote = (header + bloco).ljust(output_size, b'\x00')
        buf = C.create_string_buffer(pacote, output_size)
        written = W.DWORD()
        if not kernel.WriteFile(handle, buf, output_size, C.byref(written), None):
            raise C.WinError(C.get_last_error())
        if written.value != output_size:
            raise RuntimeError(f'Escrita incompleta: {written.value}/{output_size}')


def preparar_telas(handle, caps):
    logger.info('Configurando cores e imagens...')
    for index in range(8):
        numero = index + 1
        try:
            pintar_tecla(handle, caps.FeatureReportByteLength, index, CORES[index])
            logger.info(f'Tecla {numero}: cor aplicada')
        except OSError as e:
            logger.warning(f'Tecla {numero}: falha na cor: {e}')
        arquivo = PASTA_ICONES / f'tecla{numero}.jpg'
        if arquivo.is_file():
            dados = arquivo.read_bytes()
            if not (dados.startswith(b'\xff\xd8') and dados.endswith(b'\xff\xd9')):
                logger.warning(f'Tecla {numero}: arquivo nao parece JPEG valido: {arquivo}')
                continue
            try:
                enviar_jpeg(handle, caps.OutputReportByteLength, index, dados)
                logger.info(f'Tecla {numero}: JPEG enviado ({len(dados)} bytes)')
            except OSError as e:
                logger.error(f'Tecla {numero}: erro ao enviar JPEG: {e}')


def executar_acao(numero):
    executar_acao_log(logger, ACOES, numero)


def monitorar(handle, report_size, atualizar_display=None):
    # O primeiro relatorio pode chegar somente quando uma tecla e pressionada.
    previous = [0] * 10
    logger.info('Pressione os botoes. Ctrl+C para encerrar.')
    with ler_relatorios(kernel, handle, report_size, ao_verificar=atualizar_display) as relatorios:
        for data in relatorios:
            if len(data) < 14 or data[0] != 0x01 or data[1] != 0x00:
                continue
            states = list(data[4:14])
            for i, state in enumerate(states):
                if state == previous[i]:
                    continue
                registrar_botao(logger, ACOES, i, state)
                if state and i < 8:
                    executar_acao(i+1)
            previous = states


def main():
    logger.info('=== STREAM DECK NEO MANAGER v0.3 ===')
    logger.info('HID nativo | LCD + atalhos + relogio')
    for numero, comando in ACOES.items():
        logger.info('evento=configuracao | botao=Tecla %s | acao=%s', numero, descrever_acao(comando))
    logger.info('evento=conexao_iniciada | Procurando Stream Deck Neo')
    handle = encontrar_neo()
    logger.info('evento=conectado | Stream Deck Neo conectado')
    display_handle = None
    try:
        caps = consultar_capacidades(handle)
        preparar_telas(handle, caps)
        # ReadFile sincrono pendente serializa outras operacoes no mesmo handle.
        # Um segundo handle permite atualizar a Infobar enquanto aguardamos teclas.
        display_handle = encontrar_neo()
        relogio = RelogioDisplay(kernel, display_handle, caps.OutputReportByteLength, logger)
        monitorar(handle, caps.InputReportByteLength, relogio.atualizar)
    finally:
        if display_handle is not None:
            kernel.CloseHandle(display_handle)
        kernel.CloseHandle(handle)
        logger.info('evento=desconectado | Conexao encerrada')


if __name__ == '__main__':
    raise SystemExit(iniciar(logger, main))
