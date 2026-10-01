#!/usr/bin/env bash
set -uo pipefail

readonly DEFAULT_HOST="127.0.0.1"
readonly DEFAULT_TIMEOUT="3"

usage() {
    printf 'Uso: %s <puerto> [host] [timeout_segundos]\n' "$(basename "$0")"
    printf 'Ejemplo: %s 22\n' "$(basename "$0")"
}

es_puerto_valido() {
    local puerto="$1"
    [[ "$puerto" =~ ^[0-9]+$ ]] || return 1
    [ "$puerto" -ge 1 ] && [ "$puerto" -le 65535 ]
}

estado() {
    printf '%s|%s\n' "$1" "$2"
}

if [ "$#" -lt 1 ]; then
    usage
    exit 2
fi

PUERTO="$1"
HOST="${2:-$DEFAULT_HOST}"
TIMEOUT="${3:-$DEFAULT_TIMEOUT}"

if ! es_puerto_valido "$PUERTO"; then
    printf 'ERROR|Puerto invalido: %s (debe ser un entero entre 1 y 65535)\n' "$PUERTO" >&2
    exit 2
fi

if [ "$#" -ge 3 ] && ! [[ "$TIMEOUT" =~ ^[0-9]+$ ]]; then
    printf 'ERROR|Timeout invalido: %s\n' "$TIMEOUT" >&2
    exit 2
fi

if command -v nc >/dev/null 2>&1; then
    if nc -z -w "$TIMEOUT" "$HOST" "$PUERTO" >/dev/null 2>&1; then
        estado OPEN "El puerto $PUERTO en $HOST esta ABIERTO"
        exit 0
    else
        estado CLOSED "El puerto $PUERTO en $HOST esta CERRADO o filtrado"
        exit 1
    fi
fi

if timeout "$TIMEOUT" bash -c "exec 3<>/dev/tcp/${HOST}/${PUERTO}" >/dev/null 2>&1; then
    estado OPEN "El puerto $PUERTO en $HOST esta ABIERTO"
    exit 0
else
    estado CLOSED "El puerto $PUERTO en $HOST esta CERRADO o filtrado"
    exit 1
fi