$content = Get-Content app.py -Raw
$content = $content -replace "(login_manager.login_view = 'login'`r`n`r`n# =========================`r`n# MODELOS)", "login_manager.login_view = 'login'`r`n`r`n@login_manager.user_loader`r`ndef load_user(user_id):`r`n    return User.query.get(int(user_id))`r`n`r`n# =========================`r`n# MODELOS"
$content | Set-Content app.py