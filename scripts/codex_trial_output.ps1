# Codex --json events: https://learn.chatgpt.com/docs/non-interactive-mode
# Only a bounded final answer is retained. Raw events/tool arguments are discarded.
function Get-SafeCodexTrialOutput {
    param([string]$JsonLines, [string[]]$CredentialValues)
    $answer = ''
    $turnStatus = 'UNKNOWN'
    $parseErrors = 0
    $usage = $null
    foreach ($line in ($JsonLines -split "`n")) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $event = $line | ConvertFrom-Json -ErrorAction Stop }
        catch { $parseErrors++; continue }
        if ($event.type -eq 'item.completed' -and $event.item.type -eq 'agent_message') {
            $answer = [string]$event.item.text
        } elseif ($event.type -eq 'turn.completed') {
            $turnStatus = 'COMPLETED'
            if ($event.usage) {
                $usage = @{}
                foreach ($name in @('input_tokens','cached_input_tokens','output_tokens')) {
                    $value = $event.usage.$name
                    if ($value -is [long] -or $value -is [int]) { $usage[$name] = $value }
                }
            }
        }
        elseif ($event.type -eq 'turn.failed' -or $event.type -eq 'error') { $turnStatus = 'FAILED' }
    }
    foreach ($credential in $CredentialValues) {
        if (-not [string]::IsNullOrEmpty($credential)) { $answer = $answer.Replace($credential, '[REDACTED]') }
    }
    # Registered fake fixture sentinel and common credential-shaped text. This is
    # a bounded redactor, not a claim to discover arbitrary private information.
    $answer = [regex]::Replace($answer, '(?i)\b(?:sk-[A-Za-z0-9_-]{8,}|WH_DEMO_SECRET[A-Za-z0-9_-]*|FAKE_SECRET[A-Za-z0-9_-]*)\b', '[REDACTED]')
    $answer = [regex]::Replace($answer, '(?i)Bearer\s+[^\s]+', 'Bearer [REDACTED]')
    $answer = [regex]::Replace($answer, '[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '')
    $truncated = $answer.Length -gt 8192
    if ($truncated) { $answer = $answer.Substring(0, 8192) + '[TRUNCATED]' }
    return [pscustomobject]@{
        turn_status = $turnStatus
        masked_final_answer = $answer
        final_answer_available = -not [string]::IsNullOrEmpty($answer)
        final_answer_truncated = $truncated
        event_parse_errors = $parseErrors
        usage = $usage
    }
}
