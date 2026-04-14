; installer.iss
; Script de Inno Setup para Faprobo - Facturación, Proveeduría y Bodega
; Coloca este archivo en la raíz del proyecto (junto a pyproject.toml)

#define AppName "Faprobo - Facturación, Proveeduría y Bodega"
#define AppVersion "1.0.0"
#define AppPublisher "Faprobo"
#define AppExeName "FaproboApp.exe"
#define AppOutputName "FaproboInstaller"

[Setup]
; Identificador único de la app — NO cambiar una vez en producción
AppId={{A3F2C1D4-8B7E-4F6A-9C2D-1E5B3A7F9D0C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://faprobo.com
AppSupportURL=https://faprobo.com
AppUpdatesURL=https://faprobo.com

; Directorio de instalación por defecto
DefaultDirName={autopf}\Faprobo
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; Carpeta donde se generará el instalador final
OutputDir=output_installer
OutputBaseFilename={#AppOutputName}

; Compresión
Compression=lzma2/ultra64
SolidCompression=yes

; Requiere permisos de administrador para instalar
PrivilegesRequired=admin

; Wizard visual
WizardStyle=modern
; SetupIconFile=assets\icon.ico   ; Descomenta si agregas ícono en el futuro

; Información de la licencia (opcional)
; LicenseFile=LICENSE.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
; Opciones que el usuario puede elegir durante instalación
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
; El ejecutable generado por PyInstaller
Source: "dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Si PyInstaller genera una carpeta en lugar de un solo .exe (modo onedir),
; descomenta la siguiente línea y comenta la de arriba:
; Source: "dist\FaproboApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Acceso directo en el menú inicio
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"

; Acceso directo en escritorio (solo si el usuario lo eligió)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Ofrece ejecutar la app al terminar la instalación
Filename: "{app}\{#AppExeName}"; Description: "Iniciar {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpia archivos temporales que la app pueda generar
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
