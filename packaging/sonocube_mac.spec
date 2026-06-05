# -*- mode: python ; coding: utf-8 -*-
# macOS용 PyInstaller 스펙 파일 — onedir 모드 (.app 번들 권장)

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../model/lvseg', 'model/lvseg'),    # LV 분할 U-Net
        ('../model/v2', 'model/v2'),          # SonoCubeV2 (기본)
        ('../model/w_075', 'model/w_075'),    # 레거시 per-frame CNN
        ('../gui/assets', 'gui/assets'),      # GUI 리소스
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'numpy',
        'cv2',
        'cv2.cv2',
        'matplotlib',
        'matplotlib.backends.backend_agg',
        'matplotlib.backends.backend_qt5agg',
        'reportlab',
        'reportlab.graphics',
        'reportlab.platypus',
        'pydicom',
        'onnxruntime',
        'onnxruntime.capi._pybind_state',
        'scipy',
        'scipy.stats',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'open3d', 'pyvista', 'pyvistaqt'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# onedir 모드: EXE에 datas/binaries 포함하지 않음
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SonoCube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# COLLECT: 바이너리·datas를 별도 디렉토리로 모음
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SonoCube',
)

app = BUNDLE(
    coll,
    name='SonoCube.app',
    icon='../gui/assets/sonocube.icns',
    bundle_identifier='com.sonocube.poc',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.4.0',
        'CFBundleVersion': '1.4.0',
        'CFBundleDisplayName': 'SonoCube',
        'NSCameraUsageDescription': 'SonoCube does not use camera.',
        'NSMicrophoneUsageDescription': 'SonoCube does not use microphone.',
    },
)
