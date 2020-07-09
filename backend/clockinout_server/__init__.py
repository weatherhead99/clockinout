try:
    import importlib.metadata as metadata
except ModuleNotFoundError:
    #must be on python <3.8
    import importlib_metadata as metadata

__version__ = metadata.version(__name__)
