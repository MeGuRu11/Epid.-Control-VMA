; Inno Setup script for Epid Control VMA

#ifndef MyAppName
  #define MyAppName "Epid Control VMA"
#endif
#ifndef MyAppExeName
  #define MyAppExeName "EpidControl.exe"
#endif
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "MeGuRu11"
#endif
#define MyAppURL "https://github.com/MeGuRu11/Epid.-Control-VMA"

[Setup]
AppId={{C8E9E0B1-9A8F-4C55-9C6A-1D3F9A4F7A10}
AppName={#MyAppName}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
AppComments=Настольное приложение для эпидемиологического контроля и микробиологии
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=EpidControlSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\resources\icons\app.ico
DisableProgramGroupPage=yes
SetupLogging=yes
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Epid Control desktop installer
VersionInfoProductName={#MyAppName}
UninstallDisplayName={#MyAppName} {#MyAppVersion}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные параметры:"; Flags: unchecked

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\RELEASE_INFO.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autoprograms}\{#MyAppName}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName} сейчас"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\RELEASE_INFO.txt"

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel1.Caption := 'Установка ' + '{#MyAppName}';
  WizardForm.WelcomeLabel2.Caption :=
    '{#MyAppName} - настольное приложение для эпидемиологического контроля и микробиологии.' + #13#10 + #13#10 +
    'Мастер установит приложение, создаст деинсталлятор и, при необходимости, ярлык на рабочем столе.';
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpReady then
  begin
    WizardForm.ReadyLabel.Caption := 'Мастер готов начать установку.';
  end;

  if CurPageID = wpFinished then
  begin
    WizardForm.FinishedHeadingLabel.Caption := 'Всё готово';
    WizardForm.FinishedLabel.Caption :=
      '{#MyAppName} успешно установлен.' + #13#10 + #13#10 +
      'Можно закрыть мастер или сразу запустить приложение.';
  end;
end;
