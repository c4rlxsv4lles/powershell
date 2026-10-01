# Ejercicio: verificador de puertos TCP

Practica del modulo de **PowerShell / Seguridad**. Script que recibe un puerto como
argumento e indica si esta **ABIERTO** o **CERRADO**, en dos versiones equivalentes:
una de **Linux** (ejecutada dentro de Docker) y otra de **Windows** (PowerShell).

## Estructura

```
.
├── docker/
│   └── Dockerfile              # imagen Alpine + bash + netcat
├── scripts/
│   ├── check_port.sh           # version Linux (Bash)
│   └── check_port.ps1          # version Windows (PowerShell)
└── python/
    ├── check_ports.py          # envia multiples puertos al script chosen
    └── ports.txt               # lista de puertos de ejemplo
```

## Codigos de salida (identicos en ambos scripts)

| Codigo | Significado              |
|--------|--------------------------|
| 0      | OPEN (puerto abierto)    |
| 1      | CLOSED (cerrado/filtrado)|
| 2      | INVALID (argumentos invalidos) |

Formato de salida: `ESTADO|mensaje`

---

## 1. Version Linux con Docker

### Construir la imagen

```bash
docker build -f docker/Dockerfile -t puerto-check:local .
```

### Ejecutar

```bash
# puerto abierto en un host publico
docker run --rm puerto-check:local 443 google.com 4

# puerto cerrado
docker run --rm puerto-check:local 65000 127.0.0.1 3

# puerto invalido (espera codigo de salida 2)
docker run --rm puerto-check:local 99999

# puerto del host anfitrion desde el contenedor
docker run --rm puerto-check:local 445 host.docker.internal 4
```

Sintaxis: `check_port.sh <puerto> [host] [timeout_segundos]`
El host por defecto es `127.0.0.1` y el timeout 3 segundos.

### Ejecutar sin Docker (Linux)

```bash
chmod +x scripts/check_port.sh
./scripts/check_port.sh 22
```

---

## 2. Version Windows con PowerShell

```powershell
# puerto local
.\scripts\check_port.ps1 -Port 445

# contra un host remoto
.\scripts\check_port.ps1 -Port 443 -TargetHost google.com -TimeoutMs 2000

# forma posicional: puerto, host, timeout
.\scripts\check_port.ps1 22 127.0.0.1 1000
```

> El parametro se llama `TargetHost` porque `$Host` es una variable de **solo lectura**
> en PowerShell. Si la politica de ejecucion lo bloquea:
> `powershell -ExecutionPolicy Bypass -File .\scripts\check_port.ps1 -Port 445`

---

## 3. Orquestador en Python (multiples puertos)

Consume cualquiera de los dos scripts y muestra una tabla resumen. Detecta
automaticamente el sistema operativo: en Windows usa `check_port.ps1`, en Linux
usa `check_port.sh`.

```bash
# lista de puertos
python python/check_ports.py --ports 22,80,443

# rango inclusivo
python python/check_ports.py --range 20-25

# archivo con un puerto por linea
python python/check_ports.py --file python/ports.txt

# contra otro host, mostrando solo los abiertos
python python/check_ports.py --ports 80,443,65000 --host google.com --solo-abiertos

# forzar el script Bash por Docker (util desde Windows)
python python/check_ports.py --ports 80,443 --docker --host google.com

# forzar un interprete concreto
python python/check_ports.py --ports 80,443 --script scripts/check_port.ps1
```

Opciones: `--timeout` (segundos), `--workers` (hilos en paralelo, 5 por defecto),
`--docker-image` (imagen a usar, `puerto-check:local` por defecto).

> Cada puerto lanza un proceso externo nuevo (`powershell.exe` o un contenedor), asi que
> el tiempo total crece con la cantidad de puertos. Si aparecen estados `TIMEOUT` por
> recursos de la maquina, baja `--workers` o sube `--timeout`.

Salida esperada:

```
Script  : ...\scripts\check_port.ps1
Host    : google.com
Timeout : 3s (argumento enviado al script: 3000 ms)
Total   : 5 puerto(s)

 PUERTO  ESTADO    DETALLE
------------------------------------------------------------------------
     22  CLOSED    El puerto 22 en google.com esta CERRADO o filtrado (timeout 3000ms)
     80  OPEN      El puerto 80 en google.com esta ABIERTO
    443  OPEN      El puerto 443 en google.com esta ABIERTO
------------------------------------------------------------------------
Resumen: 2 abierto(s), 2 cerrado(s), 0 otro(s)
```

---

## 4. Como funciona la deteccion

Un puerto se considera **ABIERTO** cuando el handshake TCP se completa (el SYN
recibe un SYN/ACK); **CERRADO** cuando se recibe un RST (conexion rechazada) o
cuando la conexion expira sin respuesta (paquete filtrado por un firewall).

- **Bash**: `nc -z -w <timeout> <host> <puerto>`, con respaldo a
  `/dev/tcp` si `nc` no esta disponible.
- **PowerShell**: `System.Net.Sockets.TcpClient.ConnectAsync()` con espera
  mediante `AsyncWaitHandle.WaitOne()`.

El script Bash diferencia el caso de timeout, y PowerShell distingue la conexion
rechazada del timeout en el mensaje de detalle.

## 5. Guia del video

1. Presentacion del objetivo y la estructura del repositorio.
2. `docker build` de la imagen.
3. Pruebas del script Bash: puerto abierto, cerrado, invalido y sin argumentos,
   mostrando el codigo de salida con `echo $?`.
4. Pruebas del script PowerShell equivalentes, con `echo $LASTEXITCODE`.
5. Ejecucion de `check_ports.py` en modo PowerShell y en modo `--docker`.
6. `git add`, `git commit` y `git push` al repositorio de GitHub.