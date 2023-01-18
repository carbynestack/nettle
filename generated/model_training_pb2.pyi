from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TrainModelParameters(_message.Message):
    __slots__ = ["initialModelSecretId"]
    INITIALMODELSECRETID_FIELD_NUMBER: _ClassVar[int]
    initialModelSecretId: str
    def __init__(self, initialModelSecretId: _Optional[str] = ...) -> None: ...

class TrainModelResult(_message.Message):
    __slots__ = ["finalModelSecretId"]
    FINALMODELSECRETID_FIELD_NUMBER: _ClassVar[int]
    finalModelSecretId: str
    def __init__(self, finalModelSecretId: _Optional[str] = ...) -> None: ...
