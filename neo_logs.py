"""Logs compartilhados do Stream Deck Neo: terminal e arquivo com rotacao."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
import os


def configurar_logs(nome, pasta=None):
    logger = logging.getLogger(nome)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formato = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    terminal = logging.StreamHandler()
    terminal.setFormatter(formato)
    logger.addHandler(terminal)
    pasta = Path(pasta) if pasta is not None else (
        Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'state'))
        / 'StreamDeckNeo' / 'logs'
    )
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        arquivo = RotatingFileHandler(
            pasta / f'{nome}.log', maxBytes=5 * 1024 * 1024,
            backupCount=3, encoding='utf-8',
        )
        arquivo.setFormatter(formato)
        logger.addHandler(arquivo)
    except OSError:
        logger.exception('evento=log_arquivo_indisponivel | Logs mantidos no terminal')
    return logger


def descrever_acao(comando):
    return subprocess.list2cmdline(comando) if comando else 'sem acao configurada'


def registrar_botao(logger, acoes, indice, estado):
    nome = f'Tecla {indice + 1}' if indice < 8 else f'Sensor {indice - 7}'
    logger.info('evento=botao | botao=%s | estado=%s | acao=%s',
                nome, 'PRESSIONADO' if estado else 'SOLTO',
                descrever_acao(acoes.get(indice + 1)) if indice < 8 else 'sensor')


def executar_acao(logger, acoes, numero):
    comando = acoes.get(numero)
    descricao = descrever_acao(comando)
    if not comando:
        logger.warning('evento=acao_ausente | botao=Tecla %s | acao=%s', numero, descricao)
        return
    try:
        processo = subprocess.Popen(comando)
        logger.info('evento=acao_iniciada | botao=Tecla %s | acao=%s | pid=%s',
                    numero, descricao, processo.pid)
    except OSError:
        logger.exception('evento=acao_falhou | botao=Tecla %s | acao=%s', numero, descricao)


def iniciar(logger, main):
    logger.info('evento=inicializacao | Stream Deck Neo Manager iniciando')
    motivo = 'normal'
    try:
        main()
    except KeyboardInterrupt:
        motivo = 'ctrl_c'
        logger.info('evento=interrupcao | Encerramento solicitado pelo usuario (Ctrl+C)')
    except Exception:
        motivo = 'erro'
        logger.exception('evento=erro_fatal | Falha no Stream Deck Neo Manager')
    finally:
        logger.info('evento=finalizacao | motivo=%s', motivo)
    return 1 if motivo == 'erro' else 0
