; Narrative.Rx - Inno Setup script
; Produces NarrativeRx-Setup-<version>.exe on Windows.
;
; Prerequisites (only for building locally):
;   - Inno Setup 6+  https://jrsoftware.org/isdl.php
;   - Pre-built payload/ folder next to this .iss containing:
;       payload\backend\           (backend source + Python venv .venv\)
;       payload\frontend\build\    (yarn build output)
;       payload\nssm.exe
;       payload\mongodb-installer.msi
;       payload\narrative-rx.ico
;   (The GitHub Actions workflow at .github/workflows/build-installer.yml
;    assembles this payload automatically.)

#define AppName        "Narrative.Rx"
#define AppPublisher   "Narrative.Rx"
#define AppVersion     GetEnv("APP_VERSION")
#if AppVersion == ""
  #define AppVersion   "0.0.0-dev"
#endif
#define AppURL         "https://github.com/sb-witzy/Narrative-2"
#define AppExe         "NarrativeRx"

[Setup]
AppId={{7C4E9F1B-A2D7-4E5C-A5B1-9E5E9E1D2F44}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\Narrative.Rx
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=NarrativeRx-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=payload\narrative-rx.ico
UninstallDisplayIcon={app}\narrative-rx.ico
LicenseFile=EULA.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; Backend + pre-built venv
Source: "payload\backend\*"; DestDir: "{app}\backend"; Flags: recursesubdirs ignoreversion
; Pre-built frontend
Source: "payload\frontend\build\*"; DestDir: "{app}\frontend\build"; Flags: recursesubdirs ignoreversion
; NSSM service wrapper
Source: "payload\nssm.exe"; DestDir: "{app}"; Flags: ignoreversion
; App icon (used by shortcut + uninstaller)
Source: "payload\narrative-rx.ico"; DestDir: "{app}"; Flags: ignoreversion
; Desktop / Start Menu launcher script (pops firstrun.exe if LLM key missing,
; else opens http://localhost:8080). Referenced by shortcuts + [Run] section.
Source: "payload\open-narrative-rx.bat"; DestDir: "{app}"; Flags: ignoreversion
; First-run / settings wizard (Tkinter GUI compiled with PyInstaller)
Source: "payload\firstrun.exe"; DestDir: "{app}"; Flags: ignoreversion
; Version marker (read by backend /api/system/version)
Source: "payload\VERSION"; DestDir: "{app}"; Flags: ignoreversion
; Windows helper scripts (updater + backup)
Source: "payload\windows\*"; DestDir: "{app}\windows"; Flags: recursesubdirs ignoreversion
; MongoDB installer (chain-installed in [Run])
Source: "payload\mongodb-installer.msi"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Dirs]
; App-writable config + data + logs (survives uninstall unless user opts to remove)
Name: "{commonappdata}\NarrativeRx";         Permissions: users-modify
Name: "{commonappdata}\NarrativeRx\logs";    Permissions: users-modify

[Icons]
Name: "{autoprograms}\Narrative.Rx";        Filename: "{app}\open-narrative-rx.bat"; IconFilename: "{app}\narrative-rx.ico"
Name: "{autodesktop}\Narrative.Rx";         Filename: "{app}\open-narrative-rx.bat"; IconFilename: "{app}\narrative-rx.ico"; Tasks: desktopicon
Name: "{autoprograms}\Narrative.Rx Settings"; Filename: "{app}\firstrun.exe"; IconFilename: "{app}\narrative-rx.ico"
Name: "{autoprograms}\Uninstall Narrative.Rx"; Filename: "{uninstallexe}"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
; 1. Silent MongoDB install (only if not already installed)
Filename: "msiexec.exe"; Parameters: "/i ""{tmp}\mongodb-installer.msi"" INSTALLLOCATION=""C:\Program Files\MongoDB\Server\7.0\"" ADDLOCAL=""ServerService,Client,Router,MiscellaneousTools"" SHOULD_INSTALL_COMPASS=""0"" /qn"; StatusMsg: "Installing MongoDB (this may take a minute)..."; Check: not IsMongoInstalled

; 2. Write the .env file. EMERGENT_LLM_KEY is left blank on purpose —
;    the desktop launcher (open-narrative-rx.bat) detects the empty key
;    on first click and pops firstrun.exe so the office staffer can paste it.
Filename: "{app}\backend\.venv\Scripts\python.exe"; Parameters: "-c ""import os,secrets; from pathlib import Path; d=Path(r'{commonappdata}\NarrativeRx'); d.mkdir(parents=True, exist_ok=True); jwt=secrets.token_hex(32); Path(d/'.env').write_text('MONGO_URL=mongodb://localhost:27017\nDB_NAME=narrative_rx\nCORS_ORIGINS=http://localhost:8080\nJWT_SECRET='+jwt+'\nEMERGENT_LLM_KEY=\nADMIN_EMAIL=admin@dental.com\nADMIN_PASSWORD=admin123\nSERVE_FRONTEND=1\nMAX_CONCURRENT_LLM=3\nACTIVATION_KEY={code:GetActivationKey}\n', encoding='utf-8')"" "; StatusMsg: "Writing configuration..."; Flags: runhidden

; 3. Firewall rule for port 8080
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""Narrative.Rx (TCP 8080)"" dir=in action=allow protocol=TCP localport=8080"; StatusMsg: "Opening firewall..."; Flags: runhidden

; 4. Register + start the Windows Service
Filename: "{app}\nssm.exe"; Parameters: "install NarrativeRxApp ""{app}\backend\.venv\Scripts\python.exe"" -m uvicorn server:app --host 0.0.0.0 --port 8080"; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp AppDirectory ""{app}\backend"""; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp AppEnvironmentExtra NARRATIVE_RX_CONFIG_DIR={commonappdata}\NarrativeRx"; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp AppStdout ""{commonappdata}\NarrativeRx\logs\service-stdout.log"""; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp AppStderr ""{commonappdata}\NarrativeRx\logs\service-stderr.log"""; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp Start SERVICE_AUTO_START"; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp DependOnService MongoDB"; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "set NarrativeRxApp ObjectName LocalSystem"; Flags: runhidden
Filename: "sc.exe"; Parameters: "start NarrativeRxApp"; Flags: runhidden

; 5. Open the app in the default browser after install.
;    The launcher will pop firstrun.exe first if EMERGENT_LLM_KEY isn't set.
Filename: "{app}\open-narrative-rx.bat"; Description: "Launch Narrative.Rx"; Flags: postinstall shellexec skipifsilent nowait

[UninstallRun]
Filename: "sc.exe"; Parameters: "stop NarrativeRxApp"; Flags: runhidden
Filename: "{app}\nssm.exe"; Parameters: "remove NarrativeRxApp confirm"; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""Narrative.Rx (TCP 8080)"""; Flags: runhidden

[Code]
var
  ActivationKey: String;

// Build "NRX-XXXX-XXXX-XXXX" — 12 alphanumeric chars (uppercase, no 0/O/1/I to
// avoid transcription errors) in three dash-separated groups of 4.
// Uses a LCG seeded from GetDateTimeString('yyyymmddhhnnsszzz', ...), because
// Inno Setup Pascal Script exposes neither Randomize nor GetTickCount.
function GenerateActivationKey(): String;
var
  Alphabet, TimeStr: String;
  I, N: Integer;
  Seed: Cardinal;
  Key: String;
begin
  Alphabet := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';  // 32 chars, unambiguous
  // 17-digit timestamp with millisecond precision, no separators.
  TimeStr := GetDateTimeString('yyyymmddhhnnsszzz', #0, #0);
  Seed := 0;
  for I := 1 to Length(TimeStr) do
    Seed := Seed * 31 + Cardinal(Ord(TimeStr[I]));
  Key := 'NRX-';
  for I := 1 to 12 do begin
    // Numerical Recipes / glibc LCG constants — wraps modulo 2^32
    Seed := Seed * 1103515245 + 12345;
    N := ((Seed shr 16) mod 32) + 1;  // 1..32 → valid string index
    Key := Key + Copy(Alphabet, N, 1);
    if (I = 4) or (I = 8) then Key := Key + '-';
  end;
  Result := Key;
end;

procedure InitializeWizard();
begin
  ActivationKey := GenerateActivationKey();
end;

function GetActivationKey(Param: String): String;
begin
  Result := ActivationKey;
end;

function IsMongoInstalled(): Boolean;
begin
  Result := RegKeyExists(HKLM, 'SYSTEM\CurrentControlSet\Services\MongoDB');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  KeyFile: String;
begin
  if CurStep = ssPostInstall then begin
    // Drop a copy of the activation key at a stable path so the office can
    // retrieve it later without digging into .env.
    KeyFile := ExpandConstant('{commonappdata}\NarrativeRx\activation-key.txt');
    SaveStringToFile(KeyFile, ActivationKey + #13#10, False);
  end;
end;

// Show the generated activation key on the final wizard page so the office
// staffer can write it down before clicking Finish. Also explains that the
// Emergent LLM key will be requested by a small setup window on first launch.
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then begin
    WizardForm.FinishedLabel.Caption :=
      'Setup completed successfully.' + #13#10 + #13#10 +
      'Your practice activation key is:' + #13#10 + #13#10 +
      '        ' + ActivationKey + #13#10 + #13#10 +
      'Please note this down. It has also been saved to' + #13#10 +
      'C:\ProgramData\NarrativeRx\activation-key.txt' + #13#10 + #13#10 +
      'When you first click the Narrative.Rx icon, a small setup window' + #13#10 +
      'will appear so you can paste your Emergent LLM key' + #13#10 +
      '(app.emergent.sh -> Profile -> Universal Key).' + #13#10 + #13#10 +
      'Then log in at http://localhost:8080 with:' + #13#10 +
      '   admin@dental.com  /  admin123' + #13#10 +
      '(change the password from the Settings page once logged in)';
  end;
end;
