from functools import cached_property


def stateful_property(default_value=None, constructor=None):
    class _stateful_property(cached_property):
        def __init__(self, func):
            super().__init__(constructor or (lambda self: default_value))
            self.setter = func

        def __set__(self, instance, value):
            if instance is None:
                return self
            if self.attrname is None:
                raise TypeError(
                    "Cannot use cached_property instance without calling __set_name__ on it.")
            try:
                cache = instance.__dict__
            except AttributeError:  # not all objects have __dict__ (e.g. class defines slots)
                msg = (
                    f"No '__dict__' attribute on {type(instance).__name__!r} "
                    f"instance to cache {self.attrname!r} property."
                )
                raise TypeError(msg) from None
            with self.lock:
                # check if another thread filled cache while we awaited lock
                val = self.setter(instance, value)
                try:
                    cache[self.attrname] = val
                except TypeError:
                    msg = (
                        f"The '__dict__' attribute on {type(instance).__name__!r} instance "
                        f"does not support item assignment for caching {self.attrname!r} property."
                    )
                    raise TypeError(msg) from None

    return _stateful_property
