; اسکریپت نصب‌کنندهٔ ویندوز برای Hand Control Pro
; استفاده: ۱) build_exe.bat را اجرا کنید تا dist\HandControlPro.exe ساخته شود
;          ۲) برنامهٔ Inno Setup را نصب کنید (jrsoftware.org)
;          ۳) این فایل را با Inno Setup باز کنید و Compile را بزنید
;          خروجی: Output\HandControlPro_Setup.exe

#define AppName "Hand Control Pro"
#define AppVersion "4.0"
#define AppExe "HandControlPro.exe"

[Setup]
AppId={{3F7C1B52-8A94-4E6D-B1A7-5C2D9E04F6A8}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\HandControlPro
DefaultGroupName={#AppName}
OutputBaseFilename=HandControlPro_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "ساخت میان‌بر روی دسکتاپ"; GroupDescription: "میان‌برها:"
Name: "autostart"; Description: "اجرای خودکار همراه ویندوز (پنهان، کنار ساعت)"; GroupDescription: "شروع:"; Flags: unchecked

[Files]
Source: "dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"" --minimized"; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "اجرای {#AppName}"; Flags: nowait postinstall skipifsilent
