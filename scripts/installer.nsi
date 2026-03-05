; NSIS-установщик для Эпид. Контроль ВМА

Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma
SetCompress auto

!include "MUI2.nsh"

!ifndef APP_NAME
!define APP_NAME "Эпид. Контроль ВМА"
!endif
!ifndef APP_EXE
!define APP_EXE "EpidControl.exe"
!endif
!ifndef APP_VERSION
!define APP_VERSION "0.1.0"
!endif
!ifndef APP_PUBLISHER
!define APP_PUBLISHER "MeGuRu11"
!endif
!ifndef APP_URL
!define APP_URL "https://github.com/MeGuRu11/Epid.-Control-VMA"
!endif
!ifndef APP_DIR_NAME
!define APP_DIR_NAME "EpidControl"
!endif

!if /FileExists "${__FILEDIR__}\..\dist\${APP_EXE}"
!else
  !error "Не найден dist\\${APP_EXE}. Сначала выполните scripts\\build_exe.bat."
!endif

!if /FileExists "${__FILEDIR__}\..\dist\RELEASE_INFO.txt"
  !define HAS_RELEASE_INFO
!endif
!if /FileExists "${__FILEDIR__}\..\alembic.ini"
!else
  !error "Не найден alembic.ini в корне проекта."
!endif
!if /FileExists "${__FILEDIR__}\..\app\infrastructure\db\migrations\env.py"
!else
  !error "Не найден каталог миграций app\\infrastructure\\db\\migrations."
!endif

Name "${APP_NAME} ${APP_VERSION}"
OutFile "${__FILEDIR__}\..\dist\EpidControlSetup_NSIS.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP_DIR_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"
RequestExecutionLevel user
ShowInstDetails show
ShowUnInstDetails show
XPStyle on
BrandingText "${APP_NAME} ${APP_VERSION}"

!define MUI_ABORTWARNING
!define MUI_ICON "${__FILEDIR__}\..\resources\icons\app.ico"
!define MUI_UNICON "${__FILEDIR__}\..\resources\icons\app.ico"
!define MUI_WELCOMEPAGE_TITLE "Установка ${APP_NAME}"
!define MUI_WELCOMEPAGE_TEXT "Мастер установки поможет установить ${APP_NAME}."
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Запустить ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Страница проекта"
!define MUI_FINISHPAGE_LINK_LOCATION "${APP_URL}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Section "Файлы приложения (обязательно)" SEC_APP
  SectionIn RO
  SetShellVarContext current
  SetOutPath "$INSTDIR"
  File "${__FILEDIR__}\..\dist\${APP_EXE}"
  File "${__FILEDIR__}\..\alembic.ini"
  SetOutPath "$INSTDIR\app\infrastructure\db\migrations"
  File /r "${__FILEDIR__}\..\app\infrastructure\db\migrations\*.*"
  SetOutPath "$INSTDIR"
  !ifdef HAS_RELEASE_INFO
    File "${__FILEDIR__}\..\dist\RELEASE_INFO.txt"
  !endif

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_URL}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
SectionEnd

Section "Ярлык на рабочем столе" SEC_DESKTOP
  SetShellVarContext current
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}"
SectionEnd

Section "Ярлыки в меню Пуск" SEC_STARTMENU
  SetShellVarContext current
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\Uninstall.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_APP} "Основные файлы приложения, миграции БД и деинсталлятор."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_DESKTOP} "Создать ярлык на рабочем столе текущего пользователя."
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_STARTMENU} "Создать ярлыки в меню Пуск."
!insertmacro MUI_FUNCTION_DESCRIPTION_END

Section "un.Uninstall"
  SetShellVarContext current
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"

  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\alembic.ini"
  !ifdef HAS_RELEASE_INFO
    Delete "$INSTDIR\RELEASE_INFO.txt"
  !endif
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR\app\infrastructure\db\migrations"
  RMDir "$INSTDIR\app\infrastructure\db"
  RMDir "$INSTDIR\app\infrastructure"
  RMDir "$INSTDIR\app"
  RMDir "$INSTDIR"

  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
  DeleteRegKey HKCU "Software\${APP_NAME}"
SectionEnd
