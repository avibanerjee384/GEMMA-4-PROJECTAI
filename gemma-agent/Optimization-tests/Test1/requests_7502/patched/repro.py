
from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsRead(Protocol):
    def read(self, length: int = ...):
        ...

class FileWrapper:
    def __init__(self, fileobj):
        self._fileobj = fileobj
    def __getattr__(self, name):
        return getattr(self._fileobj, name)

class RealFile:
    def read(self, length=None):
        return "data"

rf = RealFile()
fw = FileWrapper(rf)

print(f"RealFile is SupportsRead: {isinstance(rf, SupportsRead)}")
print(f"FileWrapper is SupportsRead: {isinstance(fw, SupportsRead)}")
print(f"FileWrapper has read: {hasattr(fw, 'read')}")
