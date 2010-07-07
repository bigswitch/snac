#  Thrown each time the user changes local interface configuration
#  information

from nox.apps.pyrt.pycomponent import pyevent


# Create a functor class so that we can treat a class attribute
# as a static method.  Do this to be consistent with C++'s use 
# of static_get_name()  as a static function.

class functor:
    def __init__(self, some_method):
        self.__call__ = some_method

class interface_change_event(pyevent):

    def static_get_name_method():
        return "interface_change_event"
    static_get_name = functor(static_get_name_method)    

    def __init__(self, _interface):
        self.interface = _interface
