# -*- mode: python ; coding: utf-8 -*-


block_cipher = None

a = Analysis(['main.py'],
             pathex=['./resource'],
             binaries=[('./resource/**', 'resource')],
             datas=[],
             hiddenimports=[
                 'aiohttp',
                 'altgraph',
                 'async-timeout',
                 'attrs',
                 'cffi',
                 'chardet',
                 'commonmark',
                 'discord.py',
                 'future',
                 'idna',
                 'multidict',
                 'pefile',
                 'pycparser',
                 'Pygments',
                 'PyNaCl',
                 'pywin32-ctypes',
                 'PyYAML',
                 'rich'
                 'six',
                 'typing_extensions',
                 'yarl'],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='yomiage',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)
