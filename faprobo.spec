# faprobo.spec
# Archivo de configuración de PyInstaller para Faprobo - Facturación, Proveeduría y Bodega
# Coloca este archivo en la raíz del proyecto (junto a pyproject.toml)

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Recopila todos los submódulos de PySide6 necesarios
hidden_imports = collect_submodules('PySide6')

hidden_imports += [
    # Core
    'core.event_bus',
    'core.base_presenter',

    # Events
    'events.dashboard_events',
    'events.login_events',
    'events.producto_events',
    'events.proveedor_events',
    'events.ui_events',

    # Features - Login
    'features.login.model',
    'features.login.view',
    'features.login.presenter',

    # Features - Dashboard
    'features.dashboard.model',
    'features.dashboard.view',
    'features.dashboard.presenter',

    # Features - Productos
    'features.productos.model',
    'features.productos.view',
    'features.productos.presenter',

    # Features - Proveedores
    'features.proveedores.model',
    'features.proveedores.view',
    'features.proveedores.presenter',

    # Services (agrega aquí los módulos dentro de services/ cuando los tengas)
    # 'services.mi_servicio',
]

a = Analysis(
    ['src/main.py'],                      # Entry point
    pathex=['.', 'src'],                  # Rutas donde buscar módulos
    binaries=[],
    datas=[
        # Si tienes archivos de recursos agrégalos aquí con el formato:
        # ('ruta/origen', 'ruta/destino/dentro/del/exe')
        #
        # Ejemplos comunes:
        # ('src/ui/resources', 'ui/resources'),
        # ('src/assets', 'assets'),
        # ('src/ui/styles.qss', 'ui'),
        # ('config.yaml', '.'),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'ruff',
        'unittest',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FaproboApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='assets/icon.ico',
)