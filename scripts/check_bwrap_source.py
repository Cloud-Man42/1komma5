import inspect
from energy_core.platform.modules.isolation.sandbox import linux_bwrap

print("file", inspect.getsourcefile(linux_bwrap.LinuxBubblewrapLauncher))
print("has_socket_bind", "socket_dir" in inspect.getsource(linux_bwrap.LinuxBubblewrapLauncher.launch))
