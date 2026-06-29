from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs


hiddenimports = collect_submodules(
    'xgboost',
    filter=lambda m: not m.startswith('xgboost.testing'),
)
datas = collect_data_files('xgboost')
binaries = collect_dynamic_libs('xgboost')
