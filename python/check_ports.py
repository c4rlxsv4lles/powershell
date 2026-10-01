#!/usr/bin/env python3
"""Consume check_port.sh / check_port.ps1 enviando multiples puertos y
presenta los resultados en una tabla resumen.

Ejemplos:
    python check_ports.py --ports 22,80,443
    python check_ports.py --ports 22,80,443 --host google.com
    python check_ports.py --range 20-25
    python check_ports.py --file ports.txt
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_SH = os.path.join(RAIZ, "scripts", "check_port.sh")
SCRIPT_PS1 = os.path.join(RAIZ, "scripts", "check_port.ps1")

CODIGO_A_ESTADO = {0: "OPEN", 1: "CLOSED", 2: "INVALID"}


def detectar_script() -> Tuple[str, List[str]]:
    """Devuelve (ruta_script, prefijo_argumentos) segun el sistema operativo."""
    if platform.system().lower().startswith("win"):
        powershell = "pwsh" if _existe("pwsh") else "powershell"
        return SCRIPT_PS1, [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
    return SCRIPT_SH, ["bash"]


def _existe(comando: str) -> bool:
    from shutil import which

    return which(comando) is not None


def parsear_puertos(args: argparse.Namespace) -> List[int]:
    puertos: List[int] = []
    if args.ports:
        for token in args.ports.split(","):
            token = token.strip()
            if token:
                puertos.append(int(token))
    if args.range:
        inicio, fin = args.range.split("-")
        puertos.extend(range(int(inicio), int(fin) + 1))
    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            for linea in fh:
                limpio = linea.split("#", 1)[0].strip()
                if limpio:
                    puertos.append(int(limpio))
    vistos, unicos = set(), []
    for p in puertos:
        if p not in vistos:
            vistos.add(p)
            unicos.append(p)
    return unicos


def revisar_puerto(
    script: str,
    prefijo: List[str],
    host: str,
    puerto: int,
    timeout: int,
    proc_timeout: int,
) -> Tuple[int, str, str]:
    """Ejecuta el script externo para un puerto y devuelve (puerto, estado, detalle)."""
    comando = list(prefijo) + [script, str(puerto), host, str(timeout)]
    try:
        proc = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            shell=False,
            timeout=proc_timeout,
        )
    except subprocess.TimeoutExpired:
        return puerto, "TIMEOUT", "el script no respondio a tiempo"
    except FileNotFoundError as exc:
        return puerto, "ERROR", str(exc)

    salida = (proc.stdout or proc.stderr).strip()
    if "|" in salida:
        _, detalle = salida.split("|", 1)
        estado = CODIGO_A_ESTADO.get(proc.returncode, "ERROR")
    else:
        estado = CODIGO_A_ESTADO.get(proc.returncode, "ERROR")
        detalle = salida or "sin salida"

    if re.search(r"invalido", detalle, re.IGNORECASE):
        estado = "INVALID"
    return puerto, estado, detalle.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ports", help="lista separada por comas, ej: 22,80,443")
    parser.add_argument("--range", help="rango inclusivo, ej: 20-25")
    parser.add_argument("--file", help="archivo con un puerto por linea")
    parser.add_argument("--host", default="127.0.0.1", help="host a consultar")
    parser.add_argument("--timeout", type=int, default=3, help="timeout en segundos")
    parser.add_argument("--script", help="ruta manual a check_port.sh o check_port.ps1")
    parser.add_argument("--docker", action="store_true", help="ejecutar el script .sh via Docker")
    parser.add_argument("--docker-image", default="puerto-check:local")
    parser.add_argument("--workers", type=int, default=5, help="hilos en paralelo (5 por defecto)")
    parser.add_argument("--solo-abiertos", action="store_true", help="ocultar puertos cerrados")
    args = parser.parse_args()

    if not any([args.ports, args.range, args.file]):
        parser.error("indica --ports, --range o --file")

    try:
        puertos = parsear_puertos(args)
    except ValueError:
        parser.error("los puertos deben ser enteros validos")

    if args.docker:
        if args.script:
            parser.error("--docker y --script son excluyentes")
        script = args.docker_image
        prefijo = ["docker", "run", "--rm"]
        timeout_arg = args.timeout
        unidad = "s"
    elif args.script:
        script = os.path.abspath(args.script)
        es_ps1 = script.lower().endswith(".ps1")
        prefijo = (
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]
            if es_ps1
            else ["bash"]
        )
        timeout_arg = args.timeout * 1000 if es_ps1 else args.timeout
        unidad = "ms" if es_ps1 else "s"
    else:
        script, prefijo = detectar_script()
        es_ps1 = script.lower().endswith(".ps1")
        timeout_arg = args.timeout * 1000 if es_ps1 else args.timeout
        unidad = "ms" if es_ps1 else "s"

    if not args.docker and not os.path.isfile(script):
        print(f"ERROR: no se encontro el script {script}", file=sys.stderr)
        return 2

    print(f"Script  : {script}{' (contenedor Docker)' if args.docker else ''}")
    print(f"Host    : {args.host}")
    proc_timeout = (args.timeout + 45) if args.docker else (args.timeout + 30)
    print(f"Timeout : {args.timeout}s (argumento enviado al script: {timeout_arg} {unidad})")
    print(f"Total   : {len(puertos)} puerto(s)\n")
    print(f"{'PUERTO':>7}  {'ESTADO':<8}  DETALLE")
    print("-" * 72)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tareas = [
            pool.submit(
                revisar_puerto, script, prefijo, args.host, p, timeout_arg, proc_timeout
            )
            for p in puertos
        ]
        resultados = [t.result() for t in tareas]

    resultados.sort(key=lambda r: r[0])
    for puerto, estado, detalle in resultados:
        if args.solo_abiertos and estado != "OPEN":
            continue
        print(f"{puerto:>7}  {estado:<8}  {detalle}")

    abiertos = [r for r in resultados if r[1] == "OPEN"]
    cerrados = [r for r in resultados if r[1] == "CLOSED"]
    otros = [r for r in resultados if r[1] not in ("OPEN", "CLOSED")]

    print("-" * 72)
    print(f"Resumen: {len(abiertos)} abierto(s), {len(cerrados)} cerrado(s), {len(otros)} otro(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())