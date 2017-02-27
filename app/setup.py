from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
buildOptions = dict(packages = [], excludes = [])

base = 'Console'

executables = [
    Executable('molt.py', base=base)
]

setup(name='molt',
      version = '1.0',
      description = '',
      options = dict(build_exe = buildOptions),
      executables = executables)
