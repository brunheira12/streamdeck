"""Leitura HID sincrona sem bloquear o tratamento de Ctrl+C."""
import ctypes as C
from ctypes import wintypes as W
from contextlib import contextmanager
from queue import Queue, Empty
from threading import Event, Thread


@contextmanager
def ler_relatorios(kernel, handle, report_size, ao_verificar=None):
    if report_size <= 0:
        raise ValueError('Tamanho de Input Report invalido.')

    kernel.CancelIoEx.argtypes = [W.HANDLE, C.c_void_p]
    kernel.CancelIoEx.restype = W.BOOL
    parar = Event()
    resultados = Queue(maxsize=64)

    def publicar(resultado):
        from queue import Full
        while not parar.is_set():
            try:
                resultados.put(resultado, timeout=0.1)
                return
            except Full:
                pass

    def ler():
        try:
            while not parar.is_set():
                buffer = C.create_string_buffer(report_size)
                received = W.DWORD()
                if not kernel.ReadFile(handle, buffer, report_size, C.byref(received), None):
                    raise C.WinError(C.get_last_error())
                publicar(buffer.raw[:received.value])
        except Exception as erro:
            if not parar.is_set():
                publicar(erro)

    def relatorios():
        while True:
            if ao_verificar is not None:
                ao_verificar()
            try:
                resultado = resultados.get(timeout=0.1)
            except Empty:
                continue
            if isinstance(resultado, Exception):
                raise resultado
            yield resultado

    thread = Thread(target=ler, name='neo-hid-reader', daemon=True)
    thread.start()
    try:
        yield relatorios()
    finally:
        parar.set()
        # Repetir cobre o intervalo entre testar o evento e entrar em ReadFile.
        # Esperar a thread evita fechar o handle com uma leitura ainda pendente.
        while thread.is_alive():
            kernel.CancelIoEx(handle, None)
            thread.join(timeout=0.05)
