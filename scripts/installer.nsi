; NSIS script for EpidControl

!define APP_NAME "Epidemiological Control"
!define APP_EXE "EpidControl.exe"
!define APP_VERSION "1.0.0"
!define APP_PUBLISHER "Codex"

OutFile "${__FILEDIR__}\..\dist\EpidControlSetup_NSIS.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
RequestExecutionLevel admin
ShowInstDetails show
ShowUninstDetails show

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "${__FILEDIR__}\..\resources\icons\app.ico"
!define MUI_UNICON "${__FILEDIR__}\..\resources\icons\app.ico"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "Russian"

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  File "${__FILEDIR__}\..\dist\${APP_EXE}"
  CreateDirectory "$SMPROGRAMS\${APP_NAME}"
  CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APP_NAME}.lnk"
  Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
  RMDir "$SMPROGRAMS\${APP_NAME}"
  Delete "$INSTDIR\${APP_EXE}"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
