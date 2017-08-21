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


# Source: https://bugzilla.gnome.org/attachment.cgi?id=334199
# combined with https://github.com/virtuald/pygi-composite-templates/blob/master/gi_composites.py

from gi.repository import Gio, GLib, Gtk, GObject
from gi.repository.Gtk import _extract_handler_and_args
import os
import sys
import inspect


if sys.version_info >= (3, 0):
    _unicode = str
else:
    _unicode = unicode


def _connect_func(builder, obj, signal_name, handler_name,
                  connect_object, flags, cls):
    '''Handles GtkBuilder signal connect events'''

    if connect_object is None:
        extra = ()
    else:
        extra = (connect_object,)

    # The handler name refers to an attribute on the template instance,
    # so ask GtkBuilder for the template instance
    template_inst = builder.get_object(cls.__gtype_name__)

    handler = getattr(template_inst, handler_name)

    if flags & GObject.ConnectFlags.AFTER:
        obj.connect_after(signal_name, handler, *extra)
    else:
        obj.connect(signal_name, handler, *extra)


def _template_gclass_init(cls, gclass=None):
    if cls._template_text_:
        if isinstance(cls._template_text_, _unicode):
            template_text = cls._template_text_.encode('utf-8')
        else:
            template_text = cls._template_text_
        gbytes = GLib.Bytes.new(template_text)
        cls.set_template(gbytes)

    elif cls._template_ui_:
        cls.set_template_from_resource(cls._template_ui_)

    else:
        # If no ui file or text is given, ignore this.
        return

    cls.set_connect_func(_connect_func, cls)


def _template_ginstance_init(self):
    if self._template_text_ or self._template_ui_:
        self.init_template()


def get_template_child(widget, name):
    """Fetch an object built from the template XML for widget_type in this widget
    instance.

    :param Gtk.Widget widget_type:
        Type of the child to retrieve.
    :param str name:
        The "id" of the child defined in the template XML.

    :returns:
        A widget with "name" and "widget_type" in the template clases widget
        hiearchy or None if it was not found.

    This method will recursively search the widget hiearchy so it is a good idea
    to cache the results on a instance variable.
    """
    # Explicitly use gtk_buildable_get_name() because it is masked by
    # gtk_widget_get_name() in GI.
    if isinstance(widget, Gtk.Buildable) \
       and Gtk.Buildable.get_name(widget) == name:
        return widget

    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            result = get_template_child(child, name)
            if result is not None:
                return result


class Template(object):
    """Decorator for marking a custom Widget as a composite template.

    :param str ui:
        Filename of GTK+ Builder UI file on disk or in a gresource. Resources
        are searched first. If it fails to be a resource, then search for the
        file in the location of the Python classes file.
    :param str text:
        str or bytes containing builder xml text. Used if the `ui` argument is
        not given.
    :param str type_name:
        GObject type name to use. This must match the "class" attribute of the
        template element in the builder ui. Defaults to the Python class name.

    :returns:
        A new class which is a copy of the input class being decoratod with the
        addition of supporting composite template hooks.

    This class is for decorating Widget sub-classes which bind their child
    hierarchy directly from a Builder UI definition.

    It is important to note that signal callbacks are treated as staticmethods
    in Python terms. This means the first argument to the callback will be the
    widget emitting the signal, not the template itself. If the template itself
    is desired as the callback argument, you can bind it to the "User data"
    field and set the "Swap" field in glade for the given signal specification.
    This shows up as the "object" attribute of the "signal" element in builder
    XML as shown below.

    .. code-block:: python

        text = '''
        <interface domain="gtk30">
          <requires lib="gtk+" version="3.6"/>
          <template class="MyWidget" parent="GtkBox">
            <child>
              <object class="GtkButton" id="child_widget">
                <property name="label">Hello World</property>
                <signal name="clicked" handler="my_callback"
                        object="MyWidget" swapped="yes"/>
              </object>
            </child>
          </template>
        </interface>
        '''

        @Gtk.Template(text=text)
        class MyWidget(Gtk.Box):
            def __init__(self, **kwargs):
                super(MyWidget, self).__init__(**kwargs)
                self.child_widget = self.get_template_child('child_widget')

            @Gtk.Template.Callback
            def my_callback(self, btn):
                pass

    """
    def __init__(self, ui=None, text=None, type_name=None):
        self.ui = ui
        self.text = text
        self.type_name = type_name

    def get_template_text(self, cls):
        """Get a tuple of (ui, text) for the given class based on this template.

        If "ui" is set in the template, attempt to load its contents as a file
        from disk located in the same location as "cls".
        """
        if self.ui:
            try:
                # Try to load as a resource first
                bytes = Gio.resources_lookup_data(self.ui,
                                                  Gio.ResourceLookupFlags.NONE)

                return self.ui, None

            except GLib.Error:

                # If it fails, then try to load it as a file
                path = os.path.dirname(inspect.getfile(cls))
                path = os.path.join(path, self.ui)

                if os.path.isfile(path):
                    with open(path, 'rb') as file:
                        text = file.read()
                    return self.ui, text

        return self.ui, self.text

    def get_type_name(self, cls):
        if self.type_name is None:
            return cls.__name__
        else:
            return self.type_name

    def get_class_members(self, cls):
        # Start with a copy of the input classes dictionary.
        members = cls.__dict__.copy()

        # Remove members which might cause problems when we create
        # our new class.
        for name in ('__dict__', '__weakref__', '__gtype__'):
            if name in members:
                del members[name]

        ui, text = self.get_template_text(cls)
        type_name = self.get_type_name(cls)

        members.update({'__module__': cls.__module__,
                        '__gtype_name__': type_name,
                        '_template_ui_': ui,
                        '_template_text_': text,
                        '_gclass_init_': classmethod(_template_gclass_init),
                        '_ginstance_init_': _template_ginstance_init,
                        'get_template_child': get_template_child,
                        })

        return members

    def __call__(self, cls):
        """Create a new class which is a copy of the given cls with additional
        GObject class and instance init hooks used for Gtk.Widget templating."""

        # Generate a new sister class of the input class with additional
        # Gtk.Widget templating support.
        members = self.get_class_members(cls)
        meta_type = type(cls)
        # https://bugzilla.gnome.org/attachment.cgi?id=277355
        new_cls = meta_type(cls.__name__, cls.__bases__, members)
        _template_gclass_init(new_cls)
        return new_cls

    @staticmethod
    def Callback(f):
        '''
            Decorator that designates a method to be attached to a signal from
            the template
        '''
        return f


GtkTemplate = Template
