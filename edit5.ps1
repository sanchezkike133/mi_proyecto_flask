$content = Get-Content app.py -Raw
$content = $content -replace "@app.route('/dashboard')`r`ndef dashboard():", "@app.route('/dashboard')`r`n@login_required`r`ndef dashboard():"
$content | Set-Content app.py