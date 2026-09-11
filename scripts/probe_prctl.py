import ctypes
libc = ctypes.CDLL("libc.so.6")
print("prctl", libc.prctl(38, 1, 0, 0, 0))
