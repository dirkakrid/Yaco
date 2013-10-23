# -*- coding: utf-8 -*-
"""
Yaco
----

Yaco provides a `dict` like structure that can be serialized to & from
`yaml <http://www.yaml.org/>`_. Yaco objects behave as dictionaries
but also allow attribute access (loosely based on this `recipe <
http://code.activestate.com/recipes/473786/>`_). Sublevel dictionaries
are automatically converted to Yaco objects, allowing sublevel
attribute access, for example::

    >>> x = Yaco()
    >>> x.test = 1
    >>> x.sub.test = 2
    >>> x.sub.test
    2

Note that sub-dictionaries do not need to be initialized. This has as
a consequence that requesting uninitialized items automatically return
an empty Yaco object (inherited from a dictionary).

Yaco can be `found <http://pypi.python.org/pypi/Yaco/0.1.1>`_ in the
`Python package index <http://pypi.python.org/pypi/>`_ and is also
part of the `Moa source distribution
<https://github.com/mfiers/Moa/tree/master/lib/python/Yaco>`_

Autogenerating keys
===================

An important feature (or annoyance) of Yaco is the auto generation of
keys that are not present (yet). For example::

    >>> x = Yaco()
    >>> x.a.b.c.d = 1
    >>> assert(x.a.b.c.d == 1)

works - `a`, `b` and `c` are assumed to be `Yaco` dictionaries and d
is give value `1`. This makes populating data structures easy.

It might also generate some confusion when querying for keys in the
Yaco structure - if a key does not exists, it automatically comes back
as an empy `dict` or `Yaco` object (renders as `{}`). This means that
if it is easy to check if a certain 'branch' of a Yaco datastructure
exists::

   >>> x = Yaco()
   >>> assert (not x.a.b)

but now the following works as well:

   >>> assert('a' in x)
   >>> assert('b' in x.a )

So, a safe way to test a data structure, without introducing extra
branches is:

   >>> x = Yaco()
   >>> assert(not 'a' in x)

Todo: Need to find a more elegant way of testing without introducing
data structures

"""

import fnmatch
import logging
import os
import pkg_resources
import sys
import yaml

lg = logging.getLogger(__name__)
#lg.setLevel(logging.DEBUG)

if sys.version_info[0] == 2:
    import codecs

ITEM_INVALID = 0
ITEM_FILE = 1
ITEM_WEB = 2
ITEM_STRING = 3


class Yaco(dict):
    """
    Rather loosely based on http://code.activestate.com/recipes/473786/ (R1)

    >>> v= Yaco()
    >>> v.a = 1
    >>> assert(v.a == 1)
    >>> assert(v['a'] == 1)
    >>> v= Yaco({'a':1})
    >>> assert(v.a == 1)
    >>> assert(v['a'] == 1)

    """

    def __init__(self, data={}):
        """
        Constructor

        :param data: data to initialize the Yaco structure with
        :type data: dict or yaml formatted string
        """

        dict.__init__(self)

        if isinstance(data, dict):
            self.update(data)
        elif isinstance(data, str) or isinstance(data, bytes):
            self.update(yaml.load(data))
        else:
            raise Exception('cannot parse %s' % type(data))

    def __str__(self):
        """
        Map the structure to a string

        >>> v= Yaco({'a':1})
        >>> assert(str(v.a) == '1')
        """
        return str(self.get_data())

    def __setattr__(self, key, value):
        """
        Set the value of a key

        >>> v= Yaco()
        >>> v.a = 18
        >>> assert(v.a == 18)

        >>> v.a = 72
        >>> assert(v.a == 72)

        >>> v.a = {'b' : 5}
        >>> assert(v.a.b == 5)

        >>> v.a = {'c' : {'d' : 19}}
        >>> assert(v.a.b == 5)
        >>> assert(v.a.c.d == 19)
        >>> assert(v.a['c'].d == 19)

        >>> #create new instances on the fly
        >>> v.e = 1

        >>> v.f.g = 14
        >>> assert(v.f.g == 14)

        >>> v.f.h.i.j.k.l = 14
        >>> assert(v.f.h.i.j.k.l == 14)

        :param key: The key to set
        :param value: The value to assign to key
        """

        #print "setting %s to %s" % (key, value)
        old_value = super(Yaco, self).get(key, None)

        if isinstance(value, dict):
            #setting a dict
            if isinstance(old_value, Yaco):
                old_value.update(value)
            elif isinstance(value, Yaco):
                super(Yaco, self).__setitem__(key, value)
            else:
                super(Yaco, self).__setitem__(key, Yaco(value))

        elif isinstance(value, list):
            # parse the list to see if there are dicts - which need to
            # be translated to Yaco objects
            new_value = self._list_parser(value)
            super(Yaco, self).__setitem__(key, new_value)
        else:
            super(Yaco, self).__setitem__(key, value)

    def has_key(self, key):
        return key in list(super(Yaco, self).keys())

    def __getattr__(self, key):
        """
        >>> v= Yaco()
        >>> v.a = 18
        >>> assert(v.a == 18)
        >>> assert(isinstance(v.a, int))
        """
        try:
            return super(Yaco, self).__getitem__(key)
        except KeyError:
            rv = Yaco()
            super(Yaco, self).__setitem__(key, rv)
            return rv

    def __delattr__(self, name):
        return super(Yaco, self).__delitem__(name)

    def __getitem__(self, key):
        """
        as getattr, expect for when there is a '.' in the key.
        """
        if not '.' in key:
            return self.__getattr__(key)
        else:
            k1, k2 = key.split('.', 1)
            return self.__getattr__(k1)[k2]

    def __setitem__(self, key, value):
        """
        as setattr, except for when there is a dot in the key
        """
        if not '.' in key:
            return self.__setattr__(key, value)
        else:
            k1, k2 = key.split('.', 1)
            self.__getattr__(k1)[k2] = value

    __delitem__ = __delattr__

    def simple(self):
        """
        return a simplified representation of this
        Yaco struct - remove Yaco from the equation - and
        all object reference. Leave only bool, float, str,
        lists, tuples and dicts

        >>> x = Yaco()
        >>> x.y.z = 1
        >>> assert(isinstance(x.y, Yaco))
        >>> s = x.simple()
        >>> assert(s['y']['z'] == 1)
        >>> assert(isinstance(s['y'], dict))
        >>> assert(not isinstance(s['y'], Yaco))
        """

        def _returnSimple(item):
            if isinstance(item, (str, bool, int, float)):
                return item
            elif isinstance(item, list):
                return [_returnSimple(x) for x in item]
            elif isinstance(item, tuple):
                return (_returnSimple(x) for x in item)
            elif isinstance(item, dict):
                return dict([(k, _returnSimple(item[k]))
                             for k in item])
            else:
                return str(item)

        return _returnSimple(self)

    def _list_parser(self, old_list):
        """
        Recursively parse a list & replace all dicts with Yaco objects
        """
        for i, item in enumerate(old_list):
            if isinstance(item, dict):
                old_list[i] = Yaco(item)
            elif isinstance(item, list):
                old_list[i] = self._list_parser(item)
            else:
                pass
        return old_list


    def soft_update(self, data):
        """
        As update - but only update keys that do not have a value.

        Note - lists are completely

        >>> d1 = {'a' : [1,2,3,{'b': 12}], 'd' : {'e': 72}}
        >>> d2 = {'a' : [2,3,4,{'b': 12}], 'd' : {'e': 73, 'f': 18}, 'c' : 18}
        >>> v = Yaco(d1)
        >>> assert(v.a[2] == 3)
        >>> assert(v.d.e == 72)
        >>> v.soft_update(d2)
        >>> assert(v.d.e == 72)
        >>> assert(v.d.f == 18)
        >>> assert(v.a[2] == 3)

        """
        if not data:
            return

        for key, value in list(data.items()):

            old_value = super(Yaco, self).get(key, None)

            if isinstance(value, dict):
                if old_value and isinstance(old_value, Yaco):
                    old_value.soft_update(value)
                if old_value:
                    #there is an older value - not a dict - cannot overwrite
                    continue
                else:
                    #no old value - overwrite all you like
                    super(Yaco, self).__setitem__(key, Yaco(value))
            elif isinstance(value, list):
                # parse the list to see if there are dicts - which
                # need to be translated to Yaco objects
                if not old_value:
                    new_value = self._list_parser(value)
                    super(Yaco, self).__setitem__(key, new_value)
            else:
                if not old_value:
                    super(Yaco, self).__setitem__(key, value)

    def update(self, data):
        """
        >>> v = Yaco({'a' : [1,2,3,{'b' : 12}]})
        >>> assert(v.a[3].b == 12)

        >>> v = Yaco({'a' : [1,2,3,[1,{'b' : 12}]]})
        >>> assert(v.a[3][1].b == 12)

        """

        if not data:
            return

        for key, value in list(data.items()):

            old_value = super(Yaco, self).get(key, None)

            if isinstance(value, dict):
                if old_value and isinstance(old_value, Yaco):
                    old_value.update(value)
                else:
                    super(Yaco, self).__setitem__(key, Yaco(value))
            elif isinstance(value, list):
                # parse the list to see if there are dicts - which
                # need to be translated to Yaco objects
                new_value = self._list_parser(value)
                super(Yaco, self).__setitem__(key, new_value)
            else:
                super(Yaco, self).__setitem__(key, value)

    def copy(self):
        ch = Yaco(self)
        return ch

    def load(self, from_file, leaf=None):
        """
        Load this dict from_file

        Note - it can load the file into a leaf, instead of the root
        of this Yaco structure. Note - the leaf variable is a string,
        but may contain dots (which are automatically interpreted)

        >>> import tempfile
        >>> tf = tempfile.NamedTemporaryFile(delete=True)
        >>> tf.close()
        >>> x = Yaco({'a': [1,2,3, [1,2,3, {'d' : 4}]],
        ...           'b': 4, 'c': '5', 'uni' : "Aπ"})
        >>> x.save(tf.name)
        >>> y = Yaco()
        >>> y.load(tf.name)
        >>> assert(y.a[3][3].d == 4)
        >>> assert(sys.version_info[0] == 2 or y.uni == "Aπ")
        """
        from_file = os.path.expanduser(
                os.path.abspath(os.path.expanduser(from_file)))
        if sys.version_info[0] == 2:
            with codecs.open(from_file, encoding='utf-8') as F:
                data = yaml.load(F.read())
        else:
            with open(from_file, encoding='utf8') as F:
                data = yaml.load(F)

        if leaf is None or leaf == '':
            self.update(data)
        else:
            self[leaf].update(data)

    def pretty(self):
        """
        Return data as a pprint.pformatted string
        """
        return yaml.dump(self.get_data(), encoding='utf-8',
                         default_flow_style=False)

    def get_data(self):
        """
        Prepare & parse data for export

        >>> y = Yaco()
        >>> y.a = 1
        >>> y.b = 2
        >>> y._c = 3
        >>> assert(y._c == 3)
        >>> d = y.get_data()
        >>> assert('a' in d)
        >>> assert('b' in d)
        >>> assert(not 'c' in d)
        >>> y._private = ['b']
        >>> d = y.get_data()
        >>> assert('a' in d)
        >>> assert(not 'b' in d)
        >>> assert(not '_c' in d)
        """
        data = {}
        _priv = self.get('_private', [])

        def check_data(v):
            if isinstance(v, Yaco):
                v = v.get_data()
            elif isinstance(v, list):
                v = [check_data(x) for x in v]
            return v

        for k in list(self.keys()):
            if k in _priv:
                continue
            if isinstance(k, (str)) and k and k[0] == '_':
                continue
            data[k] = check_data(self[k])
        return data

    def dump(self):
        if sys.version_info[0] == 2:
            return yaml.safe_dump(self.get_data(),
                    default_flow_style=False)
        elif sys.version_info[0] == 3:
            return yaml.dump(self.get_data(), default_flow_style=False)

    def save(self, to_file, doNotSave=[]):
        """
        """

        data = self.get_data()
        to_file = os.path.expanduser(to_file)
        for k in list(data.keys()):
            if k in doNotSave:
                del data[k]
        if sys.version_info[0] == 2:
            with open(to_file, 'w', 0) as F:
                F.write(self.dump())
        else:
            with open(to_file, 'w', 0, encoding='utf-8') as F:
                F.write(self.dump())


class YacoFile(Yaco):
    """
    As Yaco, but loads from a file - or returns an emtpy object if it
    cannot find the file
    """

    def __init__(self, filename):
        """
        Constructor

        :param filename: filename to load
        :type filename: string
        """

        dict.__init__(self)

        self._filename = filename
        self.load()

    def load(self):
        """
        Load from the defined filename
        """
        super(YacoFile, self).load(self._filename)

    def save(self):
        """
        Load from the defined filename
        """
        super(YacoFile, self).save(self._filename)


class YacoDir(Yaco):
    """
    As Yaco, but load all files in a directory on top of each other.

    Order of loading is the alphanumerical sort of filenames

    files in subdirectories are loaded into leaves
    e.g. a file in /tmp/test/sub/a.yaml with only (x=1) will end up as follows:

        y = YacoDir('/tmp/test')
        y.sub.x == 1


    Note, YacoDir will try to cache itself in a .yacodir.cache file in the root
    of the dirname if the modification date of this file is the same as the
    directory - that will be loaded instead.
    """

    def __init__(self, dirname, pattern='*.yaml'):
        """
        Constructor

        :param dirname: directory to load
        :type dirname: string
        :param glob: a glob describing what files to load
        :type glob: string
        """

        dict.__init__(self)
        self._directory = dirname
        self._pattern = pattern
        self._cachefile = os.path.join(self._directory, '.yacodir.cache')
        self.load()

    def load(self):
        """
        Load from the defined directory
        """

        if os.path.exists(self._cachefile):
            if os.path.getmtime(self._directory) == \
                    os.path.getmtime(self._cachefile):
                #load cache
                super(YacoDir, self).load(self._cachefile)
                return

        for root, dirs, files in os.walk(self._directory):
            to_parse = sorted(fnmatch.filter(files, self._pattern))
            base = root.replace(self._directory, '').strip('/')
            base = base.replace('/', '.')
            lg.debug("{0} {1}".format(root, dirs))
            for filename in to_parse:
                fullname = os.path.join(root, filename)
                lg.debug("YacoDir loading {0}".format(fullname))
                super(YacoDir, self).load(fullname, leaf=base)

        #after loading - save to cache!
        super(YacoDir, self).save(self._cachefile)

    def save(self):
        """
        Save is disabled.
        """
        raise Exeption("Cannot save to a YacoDir")


class YacoPkg(Yaco):

    def __init__(self, pkg_name, location=None):

        if location is None:
            location = os.path.join('etc', '{}.config'.format(pkg_name))
        elif '*' in location and '/' in location:
            #probably a path:
            path, pattern = location.rsplit('/', 1)
            config = YacoPkgDir(pkg_name, path, pattern)
            self.update(config)
            return None

        try:
            config = pkg_resources.resource_string(pkg_name, location)
        except IOError:
            lg.critical("Cannot find config file for package {} @ {}".format(
                pkg_name, location))
            sys.exit(-1)

        self.update(yaml.load(config))

class YacoNotADirectory(Exception):
    pass

class YacoPkgDir(Yaco):

    def __init__(self, pkg_name, path, pattern='*.config'):

        if not pkg_resources.resource_isdir(pkg_name, path):
            raise YacoNotADirectory()

        for d in pkg_resources.resource_listdir(pkg_name, path):
            nres = os.path.join(path, d)
            if pkg_resources.resource_isdir(pkg_name, nres):
                #print 'ndir', nres
                y = YacoPkgDir(pkg_name, nres, pattern)
                self.update(y)
            else:
                if not fnmatch.fnmatch(d, pattern):
                    # print 'file - no match', nres
                    continue
                else:
                    y = YacoPkg(pkg_name, nres)
                    self.update(y)


class PolyYaco(object):
    """
    A meta object that allows a composite Yaco object to be loaded
    from any number of different files which are kept as a stack of
    Yaco objects. If looking for a value, this object will check each
    of the layers in the stack and return the first value that it
    comes across.

    Changes are only made to the toplevel object.

    The goal is to have multiple configuration files, for example in::

        /location/to/python/package/etc/config.yaml
        /etc/APPLICATION.yaml
        ~/.config/APPLICATION/config.yaml

    and have values in the latter file override those in the
    former. Saving changed values will also be done to the latter, but
    system and application wide settings can be maintained as well
    (manually for the time being).
    """

    def __init__(self, name="PY",
                 files=[], base=None, ydpattern='*.config'):
        """

        """
        self._PolyYaco_base = base
        self._PolyYaco_filenames = []
        self._PolyYaco_yacs = []
        self._PolyYaco_dirty = False
        self._PolyYaco_ydpattern = ydpattern

        #if not items - set a default
        if files is None:
            self._PolyYaco_rawfiles = [
                '/etc/{0}.config'.format(name),
                '~/.config/{0}/'.format(name) ]
        else:
            self._PolyYaco_rawfiles = files

        self.load()

    def load(self):
        """

        """
        self._PolyYaco_dirty = True
        self._PolyYaco_filenames = []
        self._PolyYaco_yacs = []
        self._PolyYaco_merged = None

        if self._PolyYaco_base is not None:
            self._PolyYaco_filenames.append('_base')
            self._PolyYaco_yacs.append(Yaco(self._PolyYaco_base))

        for filename in self._PolyYaco_rawfiles:
            filename = os.path.expanduser(filename)

            if filename[:6] == 'pkg://':
                #expecting pkg://Yaco/etc/config.yaml
                base = filename[6:]
                pkg, loc = base.split('/', 1)
                content = YacoPkg(pkg, loc)

            elif os.path.isdir(filename):
                content = YacoDir(filename, pattern = self._PolyYaco_ydpattern)
                content.load()

            elif os.path.isfile(filename):
                content = Yaco()
                content.load(filename)
            else:
                #nothing to load
                continue

            self._PolyYaco_filenames.append(filename)
            self._PolyYaco_yacs.append(content)


    def _getTop(self):
        if len(self._PolyYaco_yacs) > 0:
            return self._PolyYaco_filenames[-1], self._PolyYaco_yacs[-1]
        else:
            return None, None

    def save(self):
        cfn, cyc = self._getTop()
        if cfn == '_base':
            raise Exception("Cannot save to 'base' configuration")
        cyc.save(cfn)

    def merge(self):
        if not self._PolyYaco_dirty:
            return self._PolyYaco_merged

        y = Yaco()
        for yy in self._PolyYaco_yacs:
            y.update(yy)

        self._PolyYaco_merged = y
        self._PolyYaco_dirty = False
        return y

    def simple(self):
        return self.merge().simple()

    def __str__(self):
        return str(self.merge())

    def has_key(self, key):
        return key in self.merge()

    def __setattr__(self, key, value):
        #see if this is an instance variable
        if key[:9] == '_PolyYaco':
            self.__dict__[key] = value
            return

        self._PolyYaco_dirty = True
        cfn, cyc = self._getTop()
        cyc.__setattr__(key, value)

    def get(self, key, default=None):
        try:
            rv = self.__getattr__(key)
        except KeyError:
            return default

        if rv == {}:
            return default

        return rv


    def __contains__(self, key):
        return self.merge().__contains__(key)

    def __getattr__(self, key):
        if isinstance(key, int):
            raise Exception('No integer keys please: %s' % key)

        if key[:9] == '_PolyYaco':
            try:
                return self.__dict__[key]
            except KeyError:
                raise AttributeError()

        rv = self.merge().__getattr__(key)
        return rv

    __setitem__ = __setattr__
    __getitem__ = __getattr__



if __name__ == "__main__":
    if 'x' in sys.argv:
        y = Yaco()
        y.x.z = 1
        print(y.x.z)
    else:
        import doctest
        doctest.testmod()

