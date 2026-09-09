param(
    [string]$ContainerRuntime = "podman",
    [string]$Image = "localhost/nginx-ubi9:development"
)

$ErrorActionPreference = "Stop"
$prefix = "nginx-ubi9-smoke-$PID"
$fixedName = "$prefix-fixed"
$arbitraryName = "$prefix-arbitrary"

function Invoke-ContainerRuntime {
    param([Parameter(ValueFromRemainingArguments)] [string[]]$Arguments)

    & $ContainerRuntime @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$ContainerRuntime command failed: $($Arguments -join ' ')"
    }
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

try {
    $configuredUser = & $ContainerRuntime image inspect --format "{{.Config.User}}" $Image
    if ($LASTEXITCODE -ne 0 -or $configuredUser -ne "999:0") {
        throw "Expected image user 999:0; received $configuredUser"
    }

    Invoke-ContainerRuntime run --detach --name $fixedName `
        --read-only `
        --tmpfs "/tmp:size=64m,mode=1777" `
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

    Invoke-ContainerRuntime exec $fixedName nginx -t -q
    Invoke-ContainerRuntime exec $fixedName sh -c "test ! -w /etc/nginx/nginx.conf"
    Invoke-ContainerRuntime exec $fixedName sh -c `
        "! command -v dnf && ! command -v microdnf && ! command -v yum"

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

    Invoke-ContainerRuntime run --detach --name $arbitraryName `
        --read-only `
        --tmpfs "/tmp:size=64m,mode=1777" `
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

    Write-Output "Restricted-runtime smoke tests passed for $Image"
}
finally {
    & $ContainerRuntime rm --force $fixedName $arbitraryName 2>$null | Out-Null
}
