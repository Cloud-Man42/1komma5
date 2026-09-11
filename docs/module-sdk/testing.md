# Testing

Use `ModuleTestContext` with fakes for unit tests. Integration tests build `.emicpkg` fixtures via `build_emicpkg.py` and exercise install/update/rollback/remove through `PackageInstaller` and the admin API.
