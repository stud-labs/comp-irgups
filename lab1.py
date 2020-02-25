import sqlite3 as sql
from zope.interface import Interface, Attribute, implementer
from zope.component import adapter, getGlobalSiteManager, \
    getUtility, getAdapter, getMultiAdapter
from collections import OrderedDict
from nose.tools import raises
from zope.interface.interfaces import ComponentLookupError
import re

# Интерфейсы - явным образм описанный контракт между компонентами


class IFile(Interface):
    name = Attribute("File name")

    def size():
        """Returns size of file in bytes"""
    def content():
        """Returns content of the file as a byte array"""


class IFileCatalog(Interface):
    files = Attribute("List of files")

    def list():
        """Returns a list of files stored in"""
    def add(file):
        """Adds new file into the collection"""

# Class реадизует (implements) интерфейс


@implementer(IFile)
class VirtualFile(object):
    def __init__(self, file_name, content=b""):
        self.name = file_name
        self._content = content
        self._size = len(content)

    def content(self):
        return self._content

    def size(self):
        return self._size


@implementer(IFileCatalog)
class VirtualCatalog(object):
    def __init__(self):
        self.files = OrderedDict()

    def add(self, obj):
        """
        if IFile.providedBy(file):
            self.files[file.name] = file
        else:
            raise TypeError('IFile provider expected')
        """
        file_like = IFile(obj)
        self.files[file_like.name] = file_like

    def list(self):
        return self.files


class IImage(Interface):
    """Describes images."""
    def width():
        """Returns the width of the image."""
    def heigh():
        """Returns the heigh of the image."""
    def bpp():
        """Returns byte per pixel size."""
    def content():
        """Returns the matrix of the image."""


class IDBConnection(Interface):
    """Connection to a database"""


class IUser(Interface):
    name = Attribute("Name of the user")


class IUserCredentials(Interface):
    """User credentials"""

    def check(interface, method):
        """Checks wether user is allowed to send message
        identified by `interface` and `method` name.
        Value of `method` can be a reference or string name."""


@implementer(IImage)
class VirtualImage(object):
    def __init__(self, weight, heigh, bpp=4):
        self._w, self._h = weight, heigh
        self._bpp = bpp

    def width(self):
        return self._w

    def heigh(self):
        return self._h

    def bpp(self):
        return self._bpp

    def content(self):
        return b"#"*(self._h*self._w*self._bpp)


@implementer(IFile)
@adapter(IImage)
class AdapterOfIImageToIFile(object):
    def __init__(self, context):
        self.context = context

    def content(self):
        return self.context.content()

    @property
    def name(self):
        img = self.context
        return "Image_{}_{}_{}".format(img.width(),
                                       img.heigh(),
                                       img.bpp())

    def size(self):
        img = self.context
        return img.width()*img.heigh()*img.bpp()


@adapter(IImage, IUserCredentials)
@implementer(IImage)
class CredentialCheckingProxyForIImage(object):
    def __init__(self, context, usercred):
        self.context = context
        self.usercred = usercred

    def heigh(self):
        self.usercred.check(self.context, "heigh")
        return self.context.heigh()

    def width(self):
        self.usercred.check(self.context, "width")
        return self.context.width()

    def bpp(self):
        self.usercred.check(self.context, "bpp")
        return self.context.bpp()


GSM = getGlobalSiteManager()
GSM.registerAdapter(AdapterOfIImageToIFile)
GSM.registerAdapter(CredentialCheckingProxyForIImage, name="user-cred")
conn = sql.connect(":memory:")
GSM.registerUtility(component=conn, provided=IDBConnection, name="sqlite-conn")
del conn


class AccessDeniedException(Exception):
    def __init__(self, interface, method, message=None):
        self.interface = interface
        self.method = method
        self.message = message

    def __str__(self):
        if self.message:
            msg = self.message
        else:
            msg = ''
        msg = self.__class__.__name__ + \
            "("+msg+"for \"{}\" in interface {})"
        return msg.format(str(self.method), self.interface)


@implementer(IUser, IUserCredentials)
class TestUser(object):
    def __init__(self, name, interface, regexp=None):
        self.name = name
        self.interface = interface
        if isinstance(regexp, str):
            self.regexp = re.compile(regexp)
        else:
            self.regexp = regexp  # Including None

    def check(self, context, method):
        if isinstance(method, str):
            pass
        else:
            method = method.__name__

        if not self.interface.providedBy(context):
            raise AccessDeniedException(self.interface, method,
                                        "interface is not provided with object")

        m = self.regexp.match(method)
        if m:
            return True
        raise AccessDeniedException(self.interface, method, "access denied ")


class TestVirtualCatalog(object):
    def setUp(self):
        self.c = VirtualCatalog()
        self.f1 = VirtualFile("File1", content="Hello from File1")

    def test_test(self):
        pass

    def test_add(self):
        assert(len(self.c.list()) == 0)
        self.c.add(self.f1)
        assert(len(self.c.list()) == 1)
        assert(self.c.files[self.f1.name] == self.f1)
        print(self.c.list())

    # @raises(TypeError)
    def test_add_image(self):
        i = VirtualImage(100, 200, 1)
        self.c.add(i)
        # assert(self.c.files[self.f1.name] == self.f1)
        print(self.c.list())


class TestMarkerInterfaceStuff(object):
    def setUp(self):
        self.conn = getUtility(IDBConnection, name="sqlite-conn")
        self.tu = TestUser(name="John Lee", interface=IImage, regexp=r"^.*h$")
        self.img = VirtualImage(10, 10, 32)
        self.imgprox = getMultiAdapter((self.img, self.tu),
                                       IImage, name="user-cred")

    def test_sqlite_conn_not_none(self):
        assert(self.conn is not None)

    @raises(ComponentLookupError)
    def test_wrong_name(self):
        getUtility(IDBConnection)

    def test_cred_obj(self):
        self.tu.check(self.img, self.img.heigh)

    @raises(AccessDeniedException)
    def test_cred_obj_failed(self):
        self.tu.check(self.img, self.img.bpp)

    def test_access_to_imgproxy(self):
        self.imgprox.heigh()

    @raises(AccessDeniedException)
    def test_access_to_imgproxy_failed(self):
        self.imgprox.bpp()
