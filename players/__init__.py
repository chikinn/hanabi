"""This imports all players in this directory that are subclassed
from AIPlayer, this way you can say `from players import *`
or can say `from players import BasicRainbowPlayer`"""

__all__ = []

import pkgutil
import inspect
from hanabi_classes import AIPlayer

for loader, name, is_pkg in pkgutil.walk_packages(__path__):
    module = loader.find_module(name).load_module(name)

    for name, value in inspect.getmembers(module):
        if name.startswith('__'):
            continue

        if not inspect.isclass(value):
            continue

        # Only add it to exports if AIPlayer subclass
        if AIPlayer in value.__subclasses__():
            globals()[name] = value
            __all__.append(name)