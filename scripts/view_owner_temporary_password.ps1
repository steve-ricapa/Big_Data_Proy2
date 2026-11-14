# User-operated local viewer. No console output, clipboard, login or network use.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bytes = $null
$box = $null
try {
    $file = Join-Path $PSScriptRoot 'temporary-password.dpapi'
    $bytes = [System.Security.Cryptography.ProtectedData]::Unprotect(
        [System.IO.File]::ReadAllBytes($file), $null,
        [System.Security.Cryptography.DataProtectionScope]::CurrentUser)
    $form = New-Object System.Windows.Forms.Form
    $form.Text = 'Big Data II - ti-owner temporary password'
    $form.Size = New-Object System.Drawing.Size(660, 190)
    $form.StartPosition = 'CenterScreen'
    $label = New-Object System.Windows.Forms.Label
    $label.Text = 'Temporary password for ti-owner. Change it at your next Keycloak login.'
    $label.Location = New-Object System.Drawing.Point(15, 15)
    $label.Size = New-Object System.Drawing.Size(620, 25)
    $box = New-Object System.Windows.Forms.TextBox
    $box.Location = New-Object System.Drawing.Point(15, 50)
    $box.Size = New-Object System.Drawing.Size(610, 25)
    $box.ReadOnly = $true
    $box.UseSystemPasswordChar = $true
    $box.ShortcutsEnabled = $false
    $box.ContextMenu = New-Object System.Windows.Forms.ContextMenu
    $box.Text = [System.Text.Encoding]::UTF8.GetString($bytes)
    $show = New-Object System.Windows.Forms.CheckBox
    $show.Text = 'Show locally (do not share your screen)'
    $show.Location = New-Object System.Drawing.Point(15, 90)
    $show.Size = New-Object System.Drawing.Size(410, 25)
    $show.Add_CheckedChanged({ $box.UseSystemPasswordChar = -not $show.Checked })
    $form.Controls.AddRange(@($label, $box, $show))
    [void]$form.ShowDialog()
    $box.Text = ''
    $form.Dispose()
    $box = $null
} catch {
    [void][System.Windows.Forms.MessageBox]::Show(
        'Unable to open the private delivery. Use the same Windows account that created it.',
        'Big Data II private delivery')
} finally {
    if ($null -ne $box) { $box.Text = '' }
    if ($null -ne $bytes) { [Array]::Clear($bytes, 0, $bytes.Length) }
}
