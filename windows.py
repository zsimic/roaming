import os
import platform

P_CYGWIN = 'cygwin'
P_WINDOWS = 'windows'

APPDATA = os.environ.get('APPDATA')

if platform.system().lower().startswith('cygwin') == P_CYGWIN:
  os.environ['CYGWIN'] = "winsymlinks:nativestrict"

elif platform.system().lower() == P_WINDOWS:
  # Add support for os.symlink and os.path.islink on Windows...

  import ctypes
  from ctypes import windll
  __CSL = None
  FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
  GetFileAttributes = windll.kernel32.GetFileAttributesW

  def symlink(source, link_name):
    global __CSL
    if __CSL is None:
      csl = ctypes.windll.kernel32.CreateSymbolicLinkW
      csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
      csl.restype = ctypes.c_ubyte
      __CSL = csl
    flags = 0
    if source is not None and os.path.isdir(source):
      flags = 1
    if __CSL(link_name, source, flags) == 0:
      raise ctypes.WinError()

  def islink(path):
    res = GetFileAttributes(path)
    if res & FILE_ATTRIBUTE_REPARSE_POINT:
      return True
    else:
      return False

  os.symlink = symlink
  os.path.islink = islink
