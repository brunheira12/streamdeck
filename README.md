# Stream Deck Neo Manager

Controle do Elgato Stream Deck Neo no Windows usando Python e a API HID nativa.

## Recursos

- Ações configuráveis para as oito teclas, executadas ao pressionar.
- Cores e ícones JPEG para as teclas.
- Relógio com segundos, data e dia da semana em português na Infobar.
- Logs com data, hora, nível, botão, comando e identificação do processo iniciado.
- Encerramento com Ctrl+C e cancelamento de leituras pendentes.

## Instalação e execução

Requer Windows, Python 3.10 ou superior e um Stream Deck Neo conectado por USB.
Feche o software da Elgato antes de executar o gerenciador.

Baixe o ZIP pelo botão **Code → Download ZIP** do GitHub e extraia os arquivos.
Abra um terminal na pasta extraída:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe neo_manager_v03.py
```

Use **Ctrl+C** para encerrar.

## Configuração dos botões

Edite `ACOES` em `neo_manager_v03.py`. Cada chave representa uma tecla, de 1 a 8;
o valor contém o executável e seus argumentos. Exemplos genéricos:

```python
ACOES = {
    1: ['notepad.exe'],
    2: ['calc.exe'],
}
```

Para usar ícones próprios, salve imagens JPEG de 96 × 96 pixels, previamente
giradas em 180 graus, em `icones/tecla1.jpg` até `icones/tecla8.jpg`.
O relógio usa a data e o horário local do Windows e atualiza automaticamente.

## Logs e dados locais

Os logs ficam em `%LOCALAPPDATA%\StreamDeckNeo\logs`, fora da pasta do projeto.
Cada script mantém um arquivo de até 5 MB e três backups. Os logs podem conter
caminhos locais, comandos e identificadores do dispositivo; não os publique.
Logs, caches, ambientes virtuais e arquivos `.env` são ignorados pelo Git.
Não inclua credenciais ou caminhos pessoais nos comandos publicados.

## Arquivos

- `neo_manager_v03.py`: gerenciador com ícones e relógio.
- `neo_botoes.py`: monitor de botões e ações, sem atualização do display.
- `neo.py`: diagnóstico de identificação USB.
- `neo_hid.py`, `neo_display.py`, `neo_logs.py`: suporte compartilhado.

## Solução de problemas

Se o display parar ou o log indicar desconexão, encerre o script, reconecte o USB
e execute novamente. A escrita do relógio usa um handle separado da leitura das
teclas e tenta cancelar transferências que ultrapassem dois segundos.

Projeto independente, sem afiliação com a Elgato. Referência de protocolo:
[Stream Deck Neo HID API](https://docs.elgato.com/streamdeck/hid/stream-deck-neo/).
