# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common utility library."""

import functools
import inspect
import logging
import os
import warnings

import six
from six.moves import urllib


__author__ = [
    'rafek@google.com (Rafe Kaplan)',
    'guido@google.com (Guido van Rossum)',
]

__all__ = [
    'positional',
    'POSITIONAL_WARNING',
    'POSITIONAL_EXCEPTION',
    'POSITIONAL_IGNORE',
]

logger = logging.getLogger(__name__)

POSITIONAL_WARNING = 'WARNING'
POSITIONAL_EXCEPTION = 'EXCEPTION'
POSITIONAL_IGNORE = 'IGNORE'
POSITIONAL_SET = frozenset([POSITIONAL_WARNING, POSITIONAL_EXCEPTION,
                            POSITIONAL_IGNORE])

positional_parameters_enforcement = POSITIONAL_WARNING

_SYM_LINK_MESSAGE = 'File: {0}: Is a symbolic link.'
_IS_DIR_MESSAGE = '{0}: Is a directory'
_MISSING_FILE_MESSAGE = 'Cannot access {0}: No such file or directory'


def positional(max_positional_args):
    """A decorator to declare that only the first N arguments my be positional.

    This decorator makes it easy to support Python 3 style keyword-only
    parameters. For example, in Python 3 it is possible to write::

        def fn(pos1, *, kwonly1=None, kwonly1=None):
            ...

    All named parameters after ``*`` must be a keyword::

        fn(10, 'kw1', 'kw2')  # Raises exception.
        fn(10, kwonly1='kw1')  # Ok.

    Example
    ^^^^^^^

    To define a function like above, do::

        @positional(1)
        def fn(pos1, kwonly1=None, kwonly2=None):
            ...

    If no default value is provided to a keyword argument, it becomes a
    required keyword argument::

        @positional(0)
        def fn(required_kw):
            ...

    This must be called with the keyword parameter::

        fn()  # Raises exception.
        fn(10)  # Raises exception.
        fn(required_kw=10)  # Ok.

    When defining instance or class methods always remember to account for
    ``self`` and ``cls``::

        class MyClass(object):

            @positional(2)
            def my_method(self, pos1, kwonly1=None):
                ...

            @classmethod
            @positional(2)
            def my_method(cls, pos1, kwonly1=None):
                ...

    The positional decorator behavior is controlled by
    ``util.positional_parameters_enforcement``, which may be set to
    ``POSITIONAL_EXCEPTION``, ``POSITIONAL_WARNING`` or
    ``POSITIONAL_IGNORE`` to raise an exception, log a warning, or do
    nothing, respectively, if a declaration is violated.

    Args:
        max_positional_arguments: Maximum number of positional arguments. All
                                  parameters after the this index must be
                                  keyword only.

    Returns:
        A decorator that prevents using arguments after max_positional_args
        from being used as positional parameters.

    Raises:
        TypeError: if a key-word only argument is provided as a positional
                   parameter, but only if
                   util.positional_parameters_enforcement is set to
                   POSITIONAL_EXCEPTION.
    """

    def positional_decorator(wrapped):
        @functools.wraps(wrapped)
        def positional_wrapper(*args, **kwargs):
            if len(args) > max_positional_args:
                plural_s = ''
                if max_positional_args != 1:
                    plural_s = 's'
                message = ('{function}() takes at most {args_max} positional '
                           'argument{plural} ({args_given} given)'.format(
                               function=wrapped.__name__,
                               args_max=max_positional_args,
                               args_given=len(args),
                               plural=plural_s))
                if positional_parameters_enforcement == POSITIONAL_EXCEPTION:
                    raise TypeError(message)
                elif positional_parameters_enforcement == POSITIONAL_WARNING:
                    logger.warning(message)
            return wrapped(*args, **kwargs)
        return positional_wrapper

    if isinstance(max_positional_args, six.integer_types):
        return positional_decorator
    else:
        args, _, _, defaults = inspect.getargspec(max_positional_args)
        return positional(len(args) - len(defaults))(max_positional_args)


def scopes_to_string(scopes):
    """Converts scope value to a string.

    If scopes is a string then it is simply passed through. If scopes is an
    iterable then a string is returned that is all the individual scopes
    concatenated with spaces.

    Args:
        scopes: string or iterable of strings, the scopes.

    Returns:
        The scopes formatted as a single string.
    """
    if isinstance(scopes, six.string_types):
        return scopes
    else:
        return ' '.join(scopes)


def string_to_scopes(scopes):
    """Converts stringifed scope value to a list.

    If scopes is a list then it is simply passed through. If scopes is an
    string then a list of each individual scope is returned.

    Args:
        scopes: a string or iterable of strings, the scopes.

    Returns:
        The scopes in a list.
    """
    if not scopes:
        return []
    if isinstance(scopes, six.string_types):
        return scopes.split(' ')
    else:
        return scopes


def _add_query_parameter(url, name, value):
    """Adds a query parameter to a url.

    Replaces the current value if it already exists in the URL.

    Args:
        url: string, url to add the query parameter to.
        name: string, query parameter name.
        value: string, query parameter value.

    Returns:
        Updated query parameter. Does not update the url if value is None.
    """
    if value is None:
        return url
    else:
        parsed = list(urllib.parse.urlparse(url))
        q = dict(urllib.parse.parse_qsl(parsed[4]))
        q[name] = value
        parsed[4] = urllib.parse.urlencode(q)
        return urllib.parse.urlunparse(parsed)


def validate_file(filename):
    if os.path.islink(filename):
        raise IOError(_SYM_LINK_MESSAGE.format(filename))
    elif os.path.isdir(filename):
        raise IOError(_IS_DIR_MESSAGE.format(filename))
    elif not os.path.isfile(filename):
        warnings.warn(_MISSING_FILE_MESSAGE.format(filename))
