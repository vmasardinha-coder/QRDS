"""Serie historica oficial da B3 (ficheiros COTAHIST).

Existe porque o plano gratuito da brapi limita o historico **por ticker**:
medido no runner a 2026-08-13, PETR4 recebe 499 pregoes com range=2y enquanto
CPLE3 e MBRF3 recusam 2y, 1y e 6mo com INVALID_RANGE e so entregam 63 pregoes.
O momentum 12-1 precisa de ~273, por isso 45 dos 48 nomes eram rejeitados por
historico insuficiente e a carteira de acoes B3 parou em 100% caixa a 12/08.

A escolha desta fonte em vez do scanner do TradingView e deliberada: o
COTAHIST devolve a **serie diaria**, e nao campos ja calculados. Com serie, o
sinal fica exactamente como estava e isto e uma troca de fonte; com um retrato
pre-calculado seria uma mudanca de metodologia, que a seccao 6 da Carta trata
de outra maneira.

Formato: registo de 245 caracteres, campos em posicao fixa, precos com duas
casas decimais implicitas. Um ficheiro por ano, com todos os papeis.

O ficheiro e grande (~62 MB em 2026, ~89 MB em 2025) e cobre o mercado todo,
por isso e lido uma vez por ciclo e nao uma vez por ticker.
"""

from __future__ import annotations

import http.client
import io
import json
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

URL = "https://bvmf.bmfbovespa.com.br/InstDados/SerHist/COTAHIST_A{ano}.ZIP"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Folga sobre os ~273 pregoes do momentum 12-1, para o criterio nunca falhar
# por causa de feriados ou de um ano curto.
MIN_SESSIONS = 300
MAX_YEARS_BACK = 3

TIPREG_DETALHE = b"01"
TPMERC_VISTA = b"010"     # mercado a vista; exclui opcoes, termo e futuros

_MEMO: dict[str, list[tuple[str, float, float]]] | None = None
_PEDIDOS: set[str] = set()


class CotahistError(RuntimeError):
    """Falha a obter ou a ler o arquivo da B3.

    Deliberadamente nao herda de DataSourceError para nao criar um import
    circular; quem chama traduz.
    """


class NotLoaded(CotahistError):
    """O arquivo nao chegou a ser carregado neste ciclo.

    Separado de "este ticker nao esta no arquivo": o primeiro e a fonte em
    baixo, o segundo e um ativo que ela nao tem, e o relatorio deve distingui-los.
    """


def _cache_dir() -> Path:
    return Path(__file__).resolve().parent / "state" / "cotahist"


def _cache_path(ano: int) -> Path:
    return _cache_dir() / f"{ano}.json"


TENTATIVAS = 4
ESPERA_S = (2.0, 5.0, 12.0)


def _pedaco(url: str, desde: int, timeout: float) -> tuple[bytes, int | None]:
    """Le a partir de um deslocamento, devolvendo tambem o tamanho total.

    O servidor da B3 aceita pedidos por intervalo (responde 206), por isso um
    corte a meio retoma de onde ficou em vez de deitar fora o que ja veio.
    """
    cabecalhos = {"User-Agent": UA}
    if desde:
        cabecalhos["Range"] = f"bytes={desde}-"
    req = urllib.request.Request(url, headers=cabecalhos)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        total = None
        intervalo = resp.headers.get("Content-Range")
        if intervalo and "/" in intervalo:
            try:
                total = int(intervalo.rsplit("/", 1)[1])
            except ValueError:
                total = None
        elif resp.headers.get("Content-Length"):
            try:
                total = int(resp.headers["Content-Length"]) + desde
            except ValueError:
                total = None
        blocos = []
        while True:
            bloco = resp.read(1 << 20)
            if not bloco:
                break
            blocos.append(bloco)
        return b"".join(blocos), total


def _download(ano: int, timeout: float = 240.0) -> bytes:
    """Traz o ficheiro anual, retomando quando a ligacao corta.

    Existe assim porque a 2026-08-14 o ciclo agendado falhou com
    IncompleteRead nos 62 MB do ano corrente: um `read()` unico num ficheiro
    grande e fragil, e a queda mandou as 51 series para a brapi, que so
    entrega historico truncado. Num dia de rebalanceio isso teria liquidado a
    carteira por causa da rede, e nao por causa do sinal.
    """
    url = URL.format(ano=ano)
    dados = b""
    ultimo = ""
    for tentativa in range(TENTATIVAS):
        try:
            pedaco, total = _pedaco(url, len(dados), timeout)
            dados += pedaco
            if not pedaco:
                ultimo = "resposta vazia"
            elif total is None or len(dados) >= total:
                return dados
            else:
                ultimo = f"curto ({len(dados)}/{total} bytes)"
        except urllib.error.HTTPError as err:
            # sem retoma possivel: recomeca do principio na proxima volta
            if err.code == 416:
                dados = b""
            ultimo = f"HTTP {err.code} {err.reason}"
            if err.code in (401, 403, 404):
                break
        except (urllib.error.URLError, TimeoutError, OSError,
                http.client.HTTPException) as err:
            # so falhas de rede sao repetidas. Apanhar Exception aqui fazia um
            # erro de programacao passar por instabilidade e ser tentado quatro
            # vezes antes de aparecer disfarcado de falha de fonte.
            ultimo = type(err).__name__
        if tentativa < len(ESPERA_S):
            time.sleep(ESPERA_S[tentativa])
    raise CotahistError(f"COTAHIST {ano}: {ultimo}")


def parse(blob: bytes, wanted: set[str]) -> dict[str, list[tuple[str, float, float]]]:
    """Extrai a serie dos tickers pedidos de um ZIP anual do COTAHIST.

    Le linha a linha em bytes: o ficheiro descomprimido passa dos 500 MB e
    nao ha motivo para o trazer todo para memoria como texto.
    """
    alvo = {t.encode("latin-1") for t in wanted}
    saida: dict[bytes, list[tuple[str, float, float]]] = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile as err:
        raise CotahistError("COTAHIST: ZIP ilegivel") from err
    nomes = zf.namelist()
    if not nomes:
        raise CotahistError("COTAHIST: ZIP vazio")
    with zf.open(nomes[0]) as stream:
        for raw in stream:
            if raw[:2] != TIPREG_DETALHE or raw[24:27] != TPMERC_VISTA:
                continue
            codigo = raw[12:24].rstrip()
            if codigo not in alvo:
                continue
            try:
                # precos com duas casas decimais implicitas; quantidade inteira
                fecho = int(raw[108:121]) / 100.0
                quantidade = float(int(raw[152:170] or b"0"))
            except ValueError:
                continue          # registo corrompido: salta, nao adivinha
            if fecho <= 0:
                continue
            dia = raw[2:10].decode("latin-1")
            saida.setdefault(codigo, []).append(
                (f"{dia[:4]}-{dia[4:6]}-{dia[6:8]}", fecho, quantidade))
    return {k.decode("latin-1"): v for k, v in saida.items()}


def _year_series(ano: int, wanted: set[str], hoje: str
                 ) -> dict[str, list[tuple[str, float, float]]]:
    """Serie de um ano, da cache quando ela serve.

    Um ano ja fechado nunca muda, por isso a cache vale para sempre. O ano
    corrente e reconstruido quando a cache nao inclui o dia de hoje.
    """
    caminho = _cache_path(ano)
    corrente = ano == int(hoje[:4])
    if caminho.exists():
        try:
            guardado = json.loads(caminho.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            guardado = None
        if guardado and set(guardado.get("tickers") or []) >= wanted:
            if not corrente or guardado.get("atualizado") == hoje:
                return {k: [tuple(r) for r in v]
                        for k, v in (guardado.get("series") or {}).items()}

    series = parse(_download(ano), wanted)
    try:
        _cache_dir().mkdir(parents=True, exist_ok=True)
        caminho.write_text(json.dumps({
            "ano": ano,
            "atualizado": hoje,
            "tickers": sorted(wanted),
            "series": series,
        }), encoding="utf-8")
    except OSError:
        pass          # a cache e conveniencia; sem ela apenas se volta a puxar
    return series


def load(tickers: list[str], hoje: str | None = None
         ) -> dict[str, list[tuple[str, float, float]]]:
    """Junta os anos necessarios ate haver historico que chegue.

    Recua ano a ano em vez de assumir dois: em Janeiro, o ano corrente traz
    pregoes a menos e dois anos podiam nao cobrir os 273 do momentum.
    """
    hoje = hoje or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    wanted = {t.replace(".SA", "").upper() for t in tickers}
    juntas: dict[str, list[tuple[str, float, float]]] = {}
    erros: list[str] = []
    ano = int(hoje[:4])
    for recuo in range(MAX_YEARS_BACK):
        try:
            for ticker, linhas in _year_series(ano - recuo, wanted, hoje).items():
                juntas.setdefault(ticker, []).extend(linhas)
        except CotahistError as err:
            erros.append(str(err))
            if recuo == 0:
                raise        # sem o ano corrente nao ha preco de hoje
            break
        if juntas and max(len(v) for v in juntas.values()) >= MIN_SESSIONS:
            break
    if not juntas:
        raise CotahistError("COTAHIST sem series [" + "; ".join(erros[:2]) + "]")
    for linhas in juntas.values():
        linhas.sort(key=lambda r: r[0])
    return juntas


def prime(tickers: list[str], hoje: str | None = None) -> None:
    """Carrega o arquivo uma vez para o ciclo inteiro.

    Idempotente: as duas carteiras da B3 chamam isto, e a segunda nao deve
    voltar a puxar 150 MB.
    """
    global _MEMO, _PEDIDOS
    # comparar com o que foi pedido, e nao com o que foi encontrado: um ticker
    # que a B3 nao tenha nunca apareceria no resultado, e o arquivo voltaria a
    # ser puxado a cada chamada
    querido = {t.replace(".SA", "").upper() for t in tickers}
    if _MEMO is not None and querido <= _PEDIDOS:
        return
    _MEMO = load(tickers, hoje)
    _PEDIDOS = querido


def reset() -> None:
    global _MEMO, _PEDIDOS
    _MEMO = None
    _PEDIDOS = set()


def series_for(ticker: str) -> list[tuple[str, float, float]]:
    """Serie de um ticker ja carregado.

    Nao vai a rede: se o arquivo nao foi carregado, isso e erro de quem chama
    e nao algo para resolver em silencio a meio de um ciclo.
    """
    if _MEMO is None:
        raise NotLoaded("COTAHIST nao carregado neste ciclo")
    simbolo = ticker.replace(".SA", "").upper()
    linhas = _MEMO.get(simbolo)
    if not linhas:
        raise CotahistError(f"COTAHIST sem {simbolo}")
    return linhas
