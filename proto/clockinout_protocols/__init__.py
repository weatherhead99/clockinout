
from .clockinoutservice_pb2 import DESCRIPTOR

def get_proto_version(proto_descriptor) -> str:
    if not proto_descriptor.has_options:
        raise KeyError("proto descriptor has no options")
    opts = proto_descriptor.GetOptions()
    proto_version = None
    for flddesc, val in opts.ListFields():
        if flddesc.camelcase_name == "clockinoutProtoVersion":
            proto_version = val
            break
    if proto_version is not None:
        return proto_version
    raise ValueError("proto descriptor does not contain version number")

PROTO_SCHEMA_VERSION = get_proto_version(DESCRIPTOR)
