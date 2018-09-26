def cached_property(f, key_=None):
    '''Returns a cached property that is calculated by function f.'''
    # Source: http://code.activestate.com/recipes/576563-cached-property/
    # License: MIT

    if key_ is None:
        key_ = f

    def get(self):
        try:
            return self._property_cache[key_]
        except KeyError:
            x = self._property_cache[key_] = f(self)
            return x
        except AttributeError:
            self._property_cache = {}
            x = self._property_cache[key_] = f(self)
            return x

    def del_(self):
        del self._property_cache[key_]

    return property(get, fdel=del_)


def stateful_property(default_value=None, constructor=None):
    def wrapper(f):
        prop = cached_property(constructor or (lambda self: default_value), f)

        @prop.setter
        def prop(self, value):
            if prop.getter(self) != value:
                self._property_cache[f] = f(self, value)

        return prop

    return wrapper
