param(
    [string]$ContainerRuntime = "podman",
    [string]$Image = "localhost/nginx-ubi9:development"
)

$ErrorActionPreference = "Stop"
$prefix = "nginx-ubi9-smoke-$PID"
$fixedName = "$prefix-fixed"
$arbitraryName = "$prefix-arbitrary"
$missingTmpName = "$prefix-missing-tmp"
$invalidConfigName = "$prefix-invalid-config"

function Invoke-ContainerRuntime {
    param([Parameter(ValueFromRemainingArguments)] [string[]]$Arguments)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $ContainerRuntime @Arguments
        $runtimeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($runtimeExitCode -ne 0) {
        throw "$ContainerRuntime command failed: $($Arguments -join ' ')"
    }
}

function Get-ContainerLogs {
    param([string]$Name)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $records = & $ContainerRuntime logs $Name 2>&1
        $runtimeExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($runtimeExitCode -ne 0) {
        throw "Unable to read container logs for $Name"
    }
    return @($records | ForEach-Object { $_.ToString() })
}

function Wait-Nginx {
    param([string]$Name)

    foreach ($attempt in 1..30) {
        & $ContainerRuntime exec $Name nginx -t -q 2>$null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    }

    & $ContainerRuntime logs $Name
    throw "NGINX did not become ready in $Name"
}

function Assert-ProcessSecurity {
    param([string]$Name)

    $script = 'for status in /proc/[0-9]*/status; do uid=; cap_eff=; no_new_privs=; while IFS=: read -r key value; do case ${key} in Uid) set -- ${value}; uid=$1 ;; CapEff) set -- ${value}; cap_eff=$1 ;; NoNewPrivs) set -- ${value}; no_new_privs=$1 ;; esac; done < ${status}; test -n ${uid}; test ${uid} -ne 0; test ${cap_eff} = 0000000000000000; test ${no_new_privs} = 1; done'
    Invoke-ContainerRuntime exec $Name sh -eu -c $script
}

function Assert-TmpfsSecurity {
    param([string]$Name)

    $script = 'found=; while read -r device mount_point filesystem options remainder; do if test ${mount_point} = /tmp; then found=1; case ,${options}, in *,rw,*) : ;; *) exit 1 ;; esac; case ,${options}, in *,noexec,*) : ;; *) exit 1 ;; esac; case ,${options}, in *,nosuid,*) : ;; *) exit 1 ;; esac; case ,${options}, in *,nodev,*) : ;; *) exit 1 ;; esac; fi; done < /proc/mounts; test ${found} = 1; cp /bin/true /tmp/noexec-probe; chmod 0700 /tmp/noexec-probe; ! /tmp/noexec-probe >/dev/null 2>&1; rm -f /tmp/noexec-probe'
    Invoke-ContainerRuntime exec $Name sh -eu -c $script
}

function Assert-FailedContainer {
    param([string]$Name)

    foreach ($attempt in 1..15) {
        $state = & $ContainerRuntime inspect --format "{{.State.Status}}" $Name
        if ($LASTEXITCODE -ne 0) {
            throw "Unable to inspect failed container $Name"
        }
        if ($state -ne "running") {
            $containerExitCode = & $ContainerRuntime inspect `
                --format "{{.State.ExitCode}}" $Name
            if ($LASTEXITCODE -ne 0 -or [int]$containerExitCode -eq 0) {
                throw "Expected container $Name to exit with a failure"
            }
            return
        }
        Start-Sleep -Seconds 1
    }
    throw "Expected container $Name to exit within 15 seconds"
}

function Assert-CleanStop {
    param([string]$Name)

    Invoke-ContainerRuntime stop --time 10 $Name | Out-Null
    $containerExitCode = & $ContainerRuntime inspect `
        --format "{{.State.ExitCode}}" $Name
    if ($LASTEXITCODE -ne 0 -or [int]$containerExitCode -ne 0) {
        throw "Expected a clean exit from $Name; received $containerExitCode"
    }
}

try {
    $runtimeVersion = & $ContainerRuntime --version
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the container runtime version"
    }
    $missingTmpRuntimeArguments = @()
    if (($runtimeVersion -join "`n") -match "podman") {
        # Podman otherwise creates writable tmpfs mounts for read-only containers.
        $missingTmpRuntimeArguments += "--read-only-tmpfs=false"
    }

    $configuredUser = & $ContainerRuntime image inspect --format "{{.Config.User}}" $Image
    if ($LASTEXITCODE -ne 0 -or $configuredUser -ne "999:0") {
        throw "Expected image user 999:0; received $configuredUser"
    }

    Invoke-ContainerRuntime run --detach --name $fixedName `
        --read-only `
        --tmpfs "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --publish "127.0.0.1::8080" `
        $Image | Out-Null
    Wait-Nginx $fixedName

    $fixedUid = & $ContainerRuntime exec $fixedName id -u
    $fixedGid = & $ContainerRuntime exec $fixedName id -g
    if ($fixedUid -ne "999" -or $fixedGid -ne "0") {
        throw "Expected fixed identity 999:0; received ${fixedUid}:${fixedGid}"
    }

    Assert-ProcessSecurity $fixedName
    Assert-TmpfsSecurity $fixedName
    Invoke-ContainerRuntime exec $fixedName nginx -t -q
    Invoke-ContainerRuntime exec $fixedName sh -c "test ! -w /etc/nginx/nginx.conf"
    Invoke-ContainerRuntime exec $fixedName sh -c `
        "! command -v dnf && ! command -v microdnf && ! command -v rpm && ! command -v yum"
    Invoke-ContainerRuntime exec $fixedName sh -c `
        '! (printf probe > /root-filesystem-probe) >/dev/null 2>&1'
    Invoke-ContainerRuntime exec $fixedName sh -c `
        'read -r pid < /tmp/nginx.pid; test "${pid}" = "1"'

    $binding = & $ContainerRuntime port $fixedName "8080/tcp"
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to determine the published health port"
    }
    $hostPort = ($binding -split ":")[-1]
    $health = & curl.exe --fail --silent --show-error `
        "http://127.0.0.1:$hostPort/healthz"
    if ($LASTEXITCODE -ne 0 -or $health -ne "ok") {
        throw "Unexpected health response: $health"
    }
    $index = & curl.exe --fail --silent --show-error `
        "http://127.0.0.1:$hostPort/"
    $indexText = $index -join "`n"
    if ($LASTEXITCODE -ne 0 -or $indexText -notmatch "NGINX on UBI 9") {
        throw "The static landing page was not served"
    }

    $missingStatus = & curl.exe --silent --show-error --output NUL `
        --write-out "%{http_code}" `
        "http://127.0.0.1:$hostPort/missing?smoke-probe=value"
    if ($LASTEXITCODE -ne 0 -or $missingStatus -ne "404") {
        throw "Expected a 404 response; received $missingStatus"
    }

    $headers = & curl.exe --fail --silent --show-error --dump-header - `
        --output NUL "http://127.0.0.1:$hostPort/healthz"
    if ($LASTEXITCODE -ne 0 -or `
        -not ($headers | Where-Object { $_.Trim() -ceq "Server: nginx" })) {
        throw "The Server header was missing or disclosed the NGINX version"
    }

    $fixedLogs = Get-ContainerLogs $fixedName
    if (($fixedLogs -join "`n") -notmatch "/missing\?smoke-probe=value") {
        throw "Expected access event was not written to container logs"
    }
    if (($fixedLogs -join "`n") -match "GET /healthz") {
        throw "The health endpoint unexpectedly wrote an access event"
    }

    Invoke-ContainerRuntime exec $fixedName nginx -s reload
    $healthAfterReload = & curl.exe --fail --silent --show-error `
        "http://127.0.0.1:$hostPort/healthz"
    if ($LASTEXITCODE -ne 0 -or $healthAfterReload -ne "ok") {
        throw "Health request failed after graceful reload"
    }
    $reloadLogs = Get-ContainerLogs $fixedName
    if (($reloadLogs -join "`n") -notmatch "reconfiguring") {
        throw "NGINX did not log the graceful reload"
    }

    Invoke-ContainerRuntime run --detach --name $arbitraryName `
        --read-only `
        --tmpfs "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --user "10001:0" `
        $Image | Out-Null
    Wait-Nginx $arbitraryName

    $arbitraryUid = & $ContainerRuntime exec $arbitraryName id -u
    $arbitraryGid = & $ContainerRuntime exec $arbitraryName id -g
    if ($arbitraryUid -ne "10001" -or $arbitraryGid -ne "0") {
        throw "Expected arbitrary identity 10001:0; received ${arbitraryUid}:${arbitraryGid}"
    }

    Assert-ProcessSecurity $arbitraryName
    Assert-TmpfsSecurity $arbitraryName
    Invoke-ContainerRuntime exec $arbitraryName nginx -t -q

    Invoke-ContainerRuntime run --detach --name $missingTmpName `
        --read-only `
        @missingTmpRuntimeArguments `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        $Image | Out-Null
    Assert-FailedContainer $missingTmpName
    $missingTmpLogs = Get-ContainerLogs $missingTmpName
    if (($missingTmpLogs -join "`n") -notmatch `
        "read-only file system|/tmp/nginx.pid") {
        throw "Missing writable /tmp did not produce an actionable diagnostic"
    }

    Invoke-ContainerRuntime run --detach --name $invalidConfigName `
        --read-only `
        --tmpfs "/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777" `
        --cap-drop ALL `
        --security-opt "no-new-privileges:true" `
        --entrypoint sh `
        $Image -eu -c `
        'echo "invalid_directive;" > /tmp/invalid.conf; exec nginx -t -c /tmp/invalid.conf' `
        | Out-Null
    Assert-FailedContainer $invalidConfigName
    $invalidLogs = Get-ContainerLogs $invalidConfigName
    if (($invalidLogs -join "`n") -notmatch `
        "unknown directive.*invalid_directive|emerg") {
        throw "Invalid configuration did not produce an actionable diagnostic"
    }

    Assert-CleanStop $arbitraryName
    Assert-CleanStop $fixedName

    Write-Output "Rootless restricted-runtime scenario tests passed for $Image"
}
finally {
    & $ContainerRuntime rm --force $fixedName $arbitraryName `
        $missingTmpName $invalidConfigName 2>$null | Out-Null
}
