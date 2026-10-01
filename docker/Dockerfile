FROM alpine:3.20

LABEL maintainer="seguridad-9no"
LABEL description="Ejercicio 03 - Verificador de puertos TCP (Linux)"

RUN apk add --no-cache bash netcat-openbsd coreutils

COPY scripts/check_port.sh /usr/local/bin/check_port.sh
RUN chmod +x /usr/local/bin/check_port.sh

ENTRYPOINT ["/usr/local/bin/check_port.sh"]