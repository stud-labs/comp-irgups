from zope.interface import Interface, Attribute, implementer
from zope.component import adapter, getGlobalSiteManager
from collections import OrderedDict
from nose.tools import raises

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
    def width():
        """Returns the width of the image."""
    def heigh():
        """Returns the heigh of the image."""
    def bpp():
        """Returns byte per pixel size."""
    def content():
        """Returns the matrix of the image."""


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


GSM = getGlobalSiteManager()
GSM.registerAdapter(AdapterOfIImageToIFile)


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
