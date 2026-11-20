"""Refresh stale UI imports without clearing personal session state."""
import importlib

REVISION = 'english-20261120'
ALLOWED = {'core.journey_ui','core.data_ui','core.planning_ui'}

def fresh_ui(name):
    if name not in ALLOWED:
        raise ValueError('Unknown UI module')
    module=importlib.import_module(name)
    if getattr(module,'UI_COPY_REVISION',None)!=REVISION:
        module=importlib.reload(module)
    return module
