# -*- coding: utf-8 -*-

"""
Implementation of some flyweight patterns

https://en.wikipedia.org/wiki/Flyweight_pattern
"""

from __future__ import unicode_literals, print_function

from functools import wraps
from threading import Lock

from six import (
    iteritems, itervalues,
    add_metaclass,
)

from pynogram.utils.other import get_named_logger

LOG = get_named_logger(__name__, __file__)

'''
class CachedInstancesMeta(type):
    """
    A metaclass to store cache of every created instance
    It adds the _instances to the solver class.
    """
    _POSITIONAL_ARGS_ATTRIBUTE = '_positional_args'

    def __init__(cls, name, bases, attributes):
        super(CachedInstancesMeta, cls).__init__(name, bases, attributes)
        cls._instances = {}

    def _args_key(cls, *args, **kwargs):
        """
        Save all the args and kwargs in a tuple.

        e.g. for

        class Foo(object):
            def __init__(a, b, k=None, n=None):
                pass

        f = Foo(4, 5)
        """
        sorted_kwargs = sorted((k, v) for k, v in iteritems(kwargs))
        return ((cls._POSITIONAL_ARGS_ATTRIBUTE, tuple(args)),) + tuple(sorted_kwargs)

    def __call__(cls, *args, **kwargs):
        LOG.info('Called __call__  on %r with args=%r and kwargs=%r',
                 cls, args, kwargs)
        key = cls._args_key(*args, **kwargs)

        try:
            return cls._instances[key]
        except TypeError:  # unhashable type
            key = None
        except KeyError:
            pass

        instance = super(type(cls), cls).__call__(*args, **kwargs)
        # instance.__init__(*args, **kwargs)
        setattr(instance, cls._POSITIONAL_ARGS_ATTRIBUTE, args)
        instance._remove_from_instances_on_del = False
        instance._args_key = key

        if key is not None:
            cls._save_instance(key, instance)

        return instance

    def iter_instances(cls):
        return itervalues(cls._instances)

    def _find_by_attr_iter(cls, **attrs):
        """
        Yield all the saved instances
        with specified attribute values
        """
        for instance in cls.iter_instances():
            for attr, value in iteritems(attrs):
                inst_value = getattr(instance, attr, value)
                if inst_value != value:
                    break
            else:  # nobreak
                yield instance


@add_metaclass(CachedInstancesMeta)
class Cacheable(object):
    """
    The identity of object is completely defined by the provided arguments.
    As a result, the object can be reused if called with the same arguments.

    Name for class if valid: https://en.wiktionary.org/wiki/cacheable
    """

    __save_lock = Lock()

    @classmethod
    def _save_instance(cls, key, instance):
        with cls.__save_lock:
            cls._instances[key] = instance
            instance._remove_from_instances_on_del = True

    def __del__(self):
        """Remove self from registered _instances"""

        if self._remove_from_instances_on_del:
            if self._args_key is not None:
                print('Remove')
                LOG.info('Removing the key %r from %r instances',
                         self._args_key, self.__class__)
                del self.__class__._instances[self._args_key]
                # do not complain if key is not present
                self.__class__._instances.pop(self._args_key, None)
'''


class CachedInstancesMeta(type):
    """
    A metaclass to store cache of every created instance
    It adds the _instances to the solver class.
    """

    def __new__(mcs, *args, **kwargs):
        new_cls = super(CachedInstancesMeta, mcs).__new__(mcs, *args, **kwargs)
        new_cls._instances = {}
        return new_cls

    # def __init__(cls, name, bases, attributes):
    #     super(CachedInstancesMeta, cls).__init__(name, bases, attributes)
    #     cls._instances = {}


@add_metaclass(CachedInstancesMeta)
class Cacheable(object):
    """
    The identity of object is completely defined by the provided arguments.
    As a result, the object can be reused if called with the same arguments.

    Name for class if valid: https://en.wiktionary.org/wiki/cacheable
    """
    _POSITIONAL_ARGS_ATTRIBUTE = '_positional_args'

    def __init__(self, *args, **kwargs):
        self.__args_key = self._args_key(*args, **kwargs)
        # setattr(self, self._POSITIONAL_ARGS_ATTRIBUTE, args)

    def __new__(cls, *args, **kwargs):
        LOG.info('Called __new__  on %r with args=%r and kwargs=%r',
                 cls, args, kwargs)

        instance = super(Cacheable, cls).__new__(cls)
        instance.__init__(*args, **kwargs)
        key = instance.__args_key

        try:
            return cls._instances[key]
        except TypeError:  # unhashable type
            key = None
        except KeyError:
            pass

        if key is not None:
            cls._save_instance(key, instance)

        return instance

    __remove_from_instances_on_del = False
    __save_lock = Lock()

    @classmethod
    def _save_instance(cls, key, instance):
        with cls.__save_lock:
            cls._instances[key] = instance
            instance.__remove_from_instances_on_del = True

    @classmethod
    def iter_instances(cls):
        """Iterate over cached instances"""

        return itervalues(cls._instances)

    @classmethod
    def _find_by_attr_iter(cls, **attrs):
        """
        Yield all the saved instances
        with specified attribute values
        """
        for instance in cls.iter_instances():
            for attr, value in iteritems(attrs):
                inst_value = getattr(instance, attr, value)
                if inst_value != value:
                    break
            else:  # nobreak
                yield instance

    @classmethod
    def _args_key(cls, *args, **kwargs):
        """
        Save all the args and kwargs in a tuple.

        e.g. for

        class Foo(object):
            def __init__(a, b, k=None, n=None):
                pass

        f = Foo(4, 5,
        """
        sorted_kwargs = sorted((k, v) for k, v in iteritems(kwargs))
        return ((cls._POSITIONAL_ARGS_ATTRIBUTE, tuple(args)),) + tuple(sorted_kwargs)

    def __del__(self):
        """Remove self from registered _instances"""

        if self.__remove_from_instances_on_del:
            if self.__args_key is not None:
                LOG.info('Removing the key %r from %r instances',
                         self.__args_key, self.__class__)
                # del self.__class__._instances[self.__args_key]
                # do not complain if key is not present
                self.__class__._instances.pop(self.__args_key, None)


class UniqueChecker(Cacheable):
    """
    Subclass it to allow some fields to mark as unique.

    Prevents recreation of the second instance with the same value
    of the unique field as already created.
    """

    _UNIQUE_FIELDS = ()

    @classmethod
    def _exists(cls, **attrs):
        instance = next(cls._find_by_attr_iter(**attrs), None)
        return instance is not None

    @classmethod
    def _save_instance(cls, key, instance):
        cls.__check_unique(instance)
        super(UniqueChecker, cls)._save_instance(key, instance)

    @classmethod
    def __check_unique(cls, instance):
        for field in cls._UNIQUE_FIELDS:
            value = getattr(instance, field)
            exists = cls._exists(**{field: value})
            if exists:
                raise ValueError(
                    'Cannot create an instance with {!r}={!r} (already exists)'.format(
                        field, value))


def unique_fields(*fields):  # pragma: no cover
    """
    Use this decorator for class
    when you want to force instance creation
    with some fields to be unique
    (it prevents from creating instance with
    the same value of unique field).
    """

    def decorator(_class):
        """
        :type _class: type
        """
        name = _class.__name__
        _class.__name__ = name + '_Original'

        return type(
            name + 'Uniq',
            (UniqueChecker, _class),
            dict(_UNIQUE_FIELDS=tuple(fields))
        )

    return decorator


class SaveInstancesMeta(type):  # pragma: no cover
    """Metaclass for the type that want to manipulate with its own instances"""

    def __init__(cls, name, bases, attributes):
        super(SaveInstancesMeta, cls).__init__(name, bases, attributes)
        cls._instances = {}

    def iter_instances(cls):
        """Iterate over saved instances"""

        return itervalues(cls._instances)

    def _find_by_attr_iter(cls, **attrs):
        """
        Yield all the saved instances
        with specified attribute values
        """
        for instance in cls.iter_instances():
            for attr, value in iteritems(attrs):
                inst_value = getattr(instance, attr, value)
                if inst_value != value:
                    break
            else:  # nobreak
                yield instance


def init_once(func):
    """
    Implements common behaviour

    def some_param(self):
        if self._some_param is None:
            self._some_param = ... # init code

        return self._some_param
    """

    func_name = func.__name__
    result_member = '__result_' + func_name

    @wraps(func)
    def wrapper(arg):
        self = arg
        try:
            return getattr(self, result_member)
        except AttributeError:
            res = func(self)

            # only save the result if `func` is an instance or class method
            if hasattr(arg, func_name):
                setattr(self, result_member, res)
            return res

    return wrapper
