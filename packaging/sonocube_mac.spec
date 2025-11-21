# -*- mode: python ; coding: utf-8 -*-
# macOS용 PyInstaller 스펙 파일

block_cipher = None

a = Analysis(
    ['../main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../model', 'model'),  # 모델 파일 포함
        ('../gui/assets', 'gui/assets'),  # GUI 리소스
        ('../report/templates', 'report/templates'),  # 리포트 템플릿
    ],
    hiddenimports=[
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'numpy',
        'cv2',
        'open3d',
        'pyvista',
        'pyvistaqt',
        'matplotlib',
        'reportlab',
        'pydicom',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='SonoCube',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='SonoCube.app',
    icon=None,  # 아이콘 파일 경로 지정 가능
    bundle_identifier='com.sonocube.poc',
    info_plist={
        'NSPrincipalClass': 'NSApplication',
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
    },
)

