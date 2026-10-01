<#
.SYNOPSIS
    Verifica si un puerto TCP esta abierto o cerrado en un host.
.DESCRIPTION
    Equivalente en PowerShell de check_port.sh. Usa un socket TCP con
    timeout configurable y devuelve codigos de salida identicos al script Bash.
.PARAMETER Port
    Puerto TCP a verificar (1-65535).
.PARAMETER TargetHost
    Host o direccion IP a consultar. Por defecto 127.0.0.1.
    (se llama TargetHost porque $Host es una variable de solo lectura en PowerShell)
.PARAMETER TimeoutMs
    Tiempo maximo de espera de la conexion en milisegundos.
.EXAMPLE
    .\check_port.ps1 -Port 22
.EXAMPLE
    .\check_port.ps1 -Port 443 -TargetHost google.com -TimeoutMs 1500
.NOTES
    Codigos de salida: 0 = OPEN, 1 = CLOSED/FILTRADO, 2 = arguments invalidos.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [int]$Port,

    [Parameter(Position = 1)]
    [Alias('H')]
    [ValidateNotNullOrEmpty()]
    [string]$TargetHost = '127.0.0.1',

    [Parameter(Position = 2)]
    [int]$TimeoutMs = 3000
)

if ($Port -lt 1 -or $Port -gt 65535) {
    [Console]::Error.WriteLine("ERROR|Puerto invalido: $Port (debe ser un entero entre 1 y 65535)")
    exit 2
}

if ($TimeoutMs -lt 1) {
    [Console]::Error.WriteLine("ERROR|Timeout invalido: $TimeoutMs")
    exit 2
}

function Test-TcpPort {
    param(
        [Parameter(Mandatory = $true)][string]$ComputerName,
        [Parameter(Mandatory = $true)][int]$Port,
        [Parameter(Mandatory = $true)][int]$Timeout
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.ConnectAsync($ComputerName, $Port)
        $completado = $connect.AsyncWaitHandle.WaitOne($Timeout, $false)

        if (-not $completado) {
            return [pscustomobject]@{
                Estado     = 'CLOSED'
                Detalle    = "El puerto $Port en $ComputerName esta CERRADO o filtrado (timeout ${Timeout}ms)"
                CodigoExit = 1
            }
        }

        if ($connect.IsFaulted) {
            $motivo = $connect.Exception.InnerException.Message
            return [pscustomobject]@{
                Estado     = 'CLOSED'
                Detalle    = "El puerto $Port en $ComputerName esta CERRADO o filtrado ($motivo)"
                CodigoExit = 1
            }
        }

        return [pscustomobject]@{
            Estado     = 'OPEN'
            Detalle    = "El puerto $Port en $ComputerName esta ABIERTO"
            CodigoExit = 0
        }
    }
    catch {
        return [pscustomobject]@{
            Estado     = 'CLOSED'
            Detalle    = "El puerto $Port en $ComputerName esta CERRADO o filtrado ($($_.Exception.Message))"
            CodigoExit = 1
        }
    }
    finally {
        $client.Dispose()
    }
}

$resultado = Test-TcpPort -ComputerName $TargetHost -Port $Port -Timeout $TimeoutMs

Write-Output "$($resultado.Estado)|$($resultado.Detalle)"
exit $resultado.CodigoExit