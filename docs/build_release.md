# Сборка и релиз (Windows)

## 1) Сборка EXE
Из корня проекта:
```powershell
scripts\\build_exe.bat
```
Ожидаемый результат: `dist\\EpidControl.exe`.

## 2) Проверка сборки (DLL)
Перед установщиком проверьте наличие EXE:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\\verify_exe.ps1
```

Если используется onedir-сборка и есть каталог `dist\\_internal`, там должна быть `python312.dll`.

## 3) Сборка установщика
### NSIS
```powershell
scripts\\build_nsis.bat
```

### Inno Setup
```powershell
powershell -ExecutionPolicy Bypass -File scripts\\build_installer.ps1
```

## 4) Проверка на чистой машине
1) Установить EXE/инсталлятор.
2) Запустить приложение.
3) Убедиться, что база создается автоматически.
4) Пройти мастер "Первый запуск".

## 5) Частые ошибки
- `python312.dll not found`: проверить тип сборки и наличие `dist\\_internal\\python312.dll`.
- NSIS/ISCC не найдены: установить NSIS/Inno Setup и добавить в PATH.
