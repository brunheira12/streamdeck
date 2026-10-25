"""Relogio da Infobar do Neo (248 x 58, JPEG girado 180 graus)."""
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
from io import BytesIO
from pathlib import Path
import os
import struct
import time
from threading import Event, Timer

DIAS_SEMANA = ('Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo')


def renderizar_relogio(agora):
    from PIL import Image, ImageDraw, ImageFont

    fontes = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
    def fonte(tamanho):
        try:
            return ImageFont.truetype(str(fontes / 'segoeuib.ttf'), tamanho)
        except OSError:
            return ImageFont.load_default(size=tamanho)

    imagem = Image.new('RGB', (248, 58), (12, 17, 25))
    desenho = ImageDraw.Draw(imagem)
    desenho.text((124, 0), agora.strftime('%H:%M:%S'), font=fonte(30),
                 anchor='mt', fill=(245, 248, 255))
    data = f'{DIAS_SEMANA[agora.weekday()]} · {agora:%d/%m/%Y}'
    desenho.text((124, 36), data, font=fonte(16),
                 anchor='mt', fill=(140, 190, 230))
    saida = BytesIO()
    imagem.transpose(Image.Transpose.ROTATE_180).save(saida, format='JPEG', quality=90)
    return saida.getvalue()


def pacotes_display(jpeg, output_size):
    if output_size <= 8:
        raise ValueError('Output report pequeno demais para o display')
    capacidade = output_size - 8
    for numero, inicio in enumerate(range(0, len(jpeg), capacidade)):
        bloco = jpeg[inicio:inicio + capacidade]
        ultimo = int(inicio + len(bloco) == len(jpeg))
        header = bytes([0x02, 0x0B, 0, ultimo]) + struct.pack('<HH', len(bloco), numero)
        yield (header + bloco).ljust(output_size, b'\x00')


class RelogioDisplay:
    def __init__(self, kernel, handle, output_size, logger):
        self.kernel = kernel
        self.handle = handle
        self.output_size = output_size
        self.logger = logger
        self.ultimo = None
        self.proxima_tentativa = 0
        self.falhou = False
        self.kernel.CancelIoEx.argtypes = [W.HANDLE, C.c_void_p]
        self.kernel.CancelIoEx.restype = W.BOOL

    def enviar(self, jpeg):
        expirou = Event()
        terminou = Event()

        def cancelar():
            expirou.set()
            while not terminou.is_set():
                self.kernel.CancelIoEx(self.handle, None)
                terminou.wait(0.05)

        limite = Timer(2.0, cancelar)
        limite.daemon = True
        limite.start()
        try:
            for pacote in pacotes_display(jpeg, self.output_size):
                if expirou.is_set():
                    raise TimeoutError('Tempo limite de 2 segundos ao atualizar o display')
                buf = C.create_string_buffer(pacote, len(pacote))
                written = W.DWORD()
                if not self.kernel.WriteFile(self.handle, buf, len(pacote), C.byref(written), None):
                    if expirou.is_set():
                        raise TimeoutError('Tempo limite de 2 segundos ao atualizar o display')
                    raise C.WinError(C.get_last_error())
                if written.value != len(pacote):
                    raise OSError(f'Escrita incompleta no display: {written.value}/{len(pacote)}')
        finally:
            terminou.set()
            limite.cancel()
            limite.join()

    def atualizar(self):
        if time.monotonic() < self.proxima_tentativa:
            return
        agora = datetime.now()
        instante = agora.replace(microsecond=0)
        if instante == self.ultimo:
            return
        try:
            jpeg = renderizar_relogio(agora)
            self.enviar(jpeg)
            if self.ultimo is None or self.falhou:
                self.logger.info('evento=display_relogio_ativo | formato=HH:MM:SS DIA DD/MM/AAAA | horario=local')
            self.ultimo = instante
            self.falhou = False
        except Exception:
            self.logger.exception('evento=display_relogio_falhou | Nova tentativa em 30 segundos')
            self.falhou = True
            self.proxima_tentativa = time.monotonic() + 30
