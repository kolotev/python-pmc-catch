from pkg_resources import DistributionNotFound


try:
    _distribution = __import__('pkg_resources').get_distribution("pmc-catch")
except DistributionNotFound:  # Likely, running from working dir without installed dist
    __version__ = 'SNAPSHOT'
else:
    __version__ = _distribution.version if _distribution else 'SNAPSHOT'


from pmc.catch.core import catch


__all__ = (catch,)
