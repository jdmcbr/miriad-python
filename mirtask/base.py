'''mirtask.base - basic classes for implementing MIRIAD tasks in Python'''

# Copyright 2009, 2010 Peter Williams
#
# This file is part of miriad-python.
#
# Miriad-python is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Miriad-python is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.

import lowlevel as ll
import numpy as N
from lowlevel import MiriadError

__all__ = []

class ProgramFailError (StandardError):
    """:synopsis: Error indicating that the program cannot continue successfully.

:arg format: an explanatory message to be presented to the user
:type format: :class:`str`
:arg args: optional formatting arguments to the error string

The :class:`ProgramFailError` exception is a utility class for
aborting a high-level operation with a message to the user. It should
be raised with the expectation that the exception message will be
shown to the user without additional context. Exceptions of type
:class:`ProgramFailError` should be used sparingly in library code.
See the documentation of the module :mod:`mirtask.cliutil` for an
example way to handle :class:`ProgramFailError` exceptions specially
on the program level.

The exception message will likely be printed to the user after the
text "Error:", so it should begin with a lower-case letter.

Upon construction, the attribute :attr:`message` is initialized as
``format % args`` if *args* is nonempty. Otherwise, :attr:`message` is
set to *format*. The stringification of the exception is
``self.message``.

"""
    message = None
    """An explanatory message of why the program failed."""

    def __init__ (self, format, *args):
        if len (args) == 0:
            self.message = format
        else:
            self.message = format % args

    def __str__ (self):
        return str (self.message)

__all__ += ['ProgramFailError']


# Very simple wrapper classes. Shouldn't necessarily be used,
# given that there are standard APIs like uvdat*

class DataSet (object):
    """A generic Miriad data-set. Subclasses must implement a _close()
    method."""

    tno = None
    
    def __del__ (self):
        # tno can be None if we got an exception inside hopen,
        # or if we are deleteAll'ed

        if ll is None or self.tno is None: return

        self._close ()
        
    def __repr__ (self):
        if hasattr (self, 'name'):
            return 'DataSet (%s)' % (repr (self.name))
        return 'DataSet (<unknown filename>)'

    def __str__ (self):
        if hasattr (self, 'name'):
            nstr = '\"%s\"' % (self.name, )
        else:
            nstr = '[unknown filename]'

        if self.tno is not None:
            hstr = 'handle %d' % self.tno
        else:
            hstr = 'not currently open'

        return '<DataSet %s %s>' % (nstr, hstr)

    def isOpen (self):
        return self.tno is not None

    def _checkOpen (self):
        if self.tno is not None:
            return
        raise RuntimeError ('Illegal operation on a closed dataset')

    def close (self):
        """Close the dataset."""

        self._checkOpen ()

        if self._histOpen: self.closeHistory ()
        
        self._close ()
        self.tno = None
    
    def flush (self):
        """Write any changed items in the data set out to disk."""
        
        self._checkOpen ()
        ll.hflush (self.tno)

    def deleteAll (self):
        """Completely delete this data set. After calling this function,
        this object cannot be used."""
        
        self._checkOpen ()
        ll.hrm (self.tno)
        self.tno = None
        
    def deleteItem (self, name):
        """Delete an item from this data-set."""

        self._checkOpen ()
        ll.hdelete (self.tno, name)
    
    MODE_UNKNOWN, MODE_RD, MODE_RDWR = range (0, 3)

    def getMode (self):
        """Return the access mode of this data-set: readonly or
        read-write. See the MODE_X fields of this class for possible
        return values."""
        
        self._checkOpen ()
        mode = ll.hmode (self.tno)

        if mode == '': return self.MODE_UNKNOWN
        elif mode == 'r': return self.MODE_RD
        elif mode == 'rw': return self.MODE_RDWR
        
        raise MiriadError ('Unknown hio mode type: ' + mode)
    
    # Data items

    def hasItem (self, name):
        """Return whether this data-set contains an item with the given name."""
        
        self._checkOpen ()
        return ll.hexists (self.tno, name)

    def getItem (self, keyword, mode):
        """Return a DataItem object representing the desired item
        within this dataset. See the documentation of the DataItem
        constructor for the meaning of the 'keyword' and 'mode'
        parameters.
        """

        if keyword == '.': raise ValueError ("Use itemNames() instead.")
        
        return DataItem (self, keyword, mode)

    def itemNames (self):
        """Generate a list of the names of the data items contained in
        this data set."""
        
        ilist = DataItem (self, '.', 'r')
        s = ilist.getSize ()
        
        while ilist.getPosition () < s:
            yield ilist.seqReadString ()

        ilist.close ()

    # History

    _histOpen = False
    
    def openHistory (self, mode='a'):
        """Open the history item of this data set. 'mode' may be 
        'r' if the history is being read, 'w' for truncation and writing,
        and 'a' for appending. The default is 'a'.
        """
        
        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self._checkOpen ()
        ll.hisopen (self.tno, modestr)
        self._histOpen = True

    def writeHistory (self, text):
        """Write text into this data set's history file."""
        
        self._checkOpen ()
        ll.hiswrite (self.tno, text)

    def logInvocation (self, taskname, args=None):
        """Write text into this data set's history file logging the invocation
        of this task: when it was run and what parameters it was given. Can
        optionally be given an argument list if that contained in sys.argv
        does not represent this task."""

        self._checkOpen ()
        ll.hisinput (self.tno, taskname, args)
    
    def closeHistory (self):
        """Close this data set's history item."""

        self._checkOpen ()
        ll.hisclose (self.tno)
        self._histOpen = False

    # Header variables

    def getHeaderFloat (self, keyword, default):
        """Retrieve the value of a float-valued header variable."""

        self._checkOpen ()
        return ll.rdhdr (self.tno, keyword, float (default))

    def getHeaderInt (self, keyword, default):
        """Retrieve the value of an int-valued header variable."""

        self._checkOpen ()
        return ll.rdhdi (self.tno, keyword, int (default))

    def getHeaderBool (self, keyword, default):
        """Retrieve the value of a bool-valued header variable."""

        self._checkOpen ()
        return bool (ll.rdhdl (self.tno, keyword, int (default)))

    def getHeaderDouble (self, keyword, default):
        """Retrieve the value of a double-valued header variable."""

        self._checkOpen ()
        return ll.rdhdd (self.tno, keyword, float (default))

    def getHeaderComplex (self, keyword, default):
        """Retrieve the value of a complex-valued header variable."""

        self._checkOpen ()
        return ll.rdhdc (self.tno, keyword, complex (default))
    
    def getHeaderString (self, keyword, default):
        """Retrieve the value of a string-valued header variable.
        Maximum value length is 512."""

        self._checkOpen ()
        return ll.rdhda (self.tno, keyword, str (default))

    def writeHeaderFloat (self, keyword, value):
        """Write a float-valued header variable."""
        self._checkOpen ()
        ll.wrhdr (self.tno, keyword, float (value))

    def writeHeaderInt (self, keyword, value):
        """Write an int-valued header variable."""
        self._checkOpen ()
        ll.wrhdi (self.tno, keyword, int (value))

    def writeHeaderLong (self, keyword, value):
        """Write a long-int-valued header variable."""
        self._checkOpen ()
        ll.wrhdl (self.tno, keyword, int (value))

    def writeHeaderDouble (self, keyword, value):
        """Write a double-valued header variable."""
        self._checkOpen ()
        ll.wrhdd (self.tno, keyword, float (value))

    def writeHeaderComplex (self, keyword, value):
        """Write a complex-valued header variable."""
        self._checkOpen ()
        ll.wrhdc (self.tno, keyword, complex (value))
    
    def writeHeaderString (self, keyword, value):
        """Write a string-valued header variable."""
        self._checkOpen ()
        ll.wrhda (self.tno, keyword, str (value))

    def copyHeader (self, dest, keyword):
        """Copy a header variable from this data-set to another."""

        self._checkOpen ()
        ll.hdcopy (self.tno, dest.tno, keyword)

    # skip hdprsnt: same thing as hexists
    
    def getHeaderInfo (self, keyword):
        """Return the characteristics of the header variable. Returns:
        (desc, type, n), where 'desc' describes the item or gives its value
        if it can be expressed compactly; 'type' is one of 'nonexistant',
        'integer*2', 'integer*8', 'integer', 'real', 'double', 'complex',
        'character', 'text', or 'binary'; and 'n' is the number of elements
        in the item. If 'n' is 1, then 'desc' encodes the item's value.
        """

        self._checkOpen ()
        (desc, type, n) = ll.hdprobe (self.tno, keyword)

        if n == 0: raise MiriadError ('Error probing header ' + keyword)

        return (desc, type, n)

class DataItem (object):
    """An item contained within a Miriad dataset."""

    itno = None

    def __init__ (self, dataset, keyword, mode):
        self.dataset = dataset
        self.refobj = dataset.refobj
        self.name = keyword

        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        elif mode == 's': modestr = 'scratch'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.itno = ll.haccess (dataset.tno, keyword, modestr)

    def __del__ (self):
        # itno can be None if we got an exception inside haccess.

        if ll is None or self.itno is None: return
        self.close ()

    def close (self):
        ll.hdaccess (self.itno)
        self.itno = None

    def _checkOpen (self):
        if self.itno is not None:
            return
        raise RuntimeError ('Illegal operation on a closed dataset')

    def isOpen (self):
        return self.itno is not None

    def getSize (self):
        """Return the size of this data item."""

        self._checkOpen ()
        return ll.hsize (self.itno)

    def seek (self, offset):
        """Seek to the specified position within this data item."""

        self._checkOpen ()
        ll.hseek (self.itno, int (offset))

    def getPosition (self):
        """Retrieve the current position within this data item."""

        self._checkOpen ()
        return ll.htell (self.itno)

    def seqReadString (self):
        """Read until newline from the current position within this
        data item. Maximum string length of 512."""

        self._checkOpen ()
        return ll.hreada (self.itno)

    def seqWriteString (self, line, length=None):
        """Write a textual string into the data item, terminating
        the string with a newline. If desired, only a subset of the
        string can be written out; the default is to write the
        entire string."""

        if length is None: length = len (line)
        self._checkOpen ()
        ll.hwritea (self.itno, str (line), length)

    # Reading buffers
    
    def readBytes (self, buf, offset, length=None):
        """Read an array of bytes from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.byte)
        if length is None: length = buf.size
        ll.hreadb (self.itno, buf, offset, length)

    def readInts (self, buf, offset, length=None):
        """Read an array of 32-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int)
        if length is None: length = buf.size
        ll.hreadi (self.itno, buf, offset, length)

    def readShorts (self, buf, offset, length=None):
        """Read an array of 16-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.short)
        if length is None: length = buf.size
        ll.hreadj (self.itno, buf, offset, length)

    def readLongs (self, buf, offset, length=None):
        """Read an array of 64-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.long)
        if length is None: length = buf.size
        ll.hreadl (self.itno, buf, offset, length)

    def readFloats (self, buf, offset, length=None):
        """Read an array of floats from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.float)
        if length is None: length = buf.size
        ll.hreadr (self.itno, buf, offset, length)

    def readDoubles (self, buf, offset, length=None):
        """Read an array of doubles from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.double)
        if length is None: length = buf.size
        ll.hreadd (self.itno, buf, offset, length)

    def readComplex (self, buf, offset, length=None):
        """Read an array of complexes from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.complex64)
        if length is None: length = buf.size
        ll.hreadc (self.itno, buf, offset, length)

    # Writing
    
    def writeBytes (self, buf, offset, length=None):
        """Write an array of bytes to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.byte)
        if length is None: length = buf.size
        ll.hwriteb (self.itno, buf, offset, length)

    def writeInts (self, buf, offset, length=None):
        """Write an array of integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int)
        if length is None: length = buf.size
        ll.hwritei (self.itno, buf, offset, length)

    def writeShorts (self, buf, offset, length=None):
        """Write an array of 16-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.short)
        if length is None: length = buf.size
        ll.hwritej (self.itno, buf, offset, length)

    def writeLongs (self, buf, offset, length=None):
        """Write an array of 64-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.long)
        if length is None: length = buf.size
        ll.hwritel (self.itno, buf, offset, length)

    def writeFloats (self, buf, offset, length=None):
        """Write an array of floats to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.float)
        if length is None: length = buf.size
        ll.hwriter (self.itno, buf, offset, length)

    def writeDoubles (self, buf, offset, length=None):
        """Write an array of doubles to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.double)
        if length is None: length = buf.size
        ll.hwrited (self.itno, buf, offset, length)

    def writeComplex (self, buf, offset, length=None):
        """Write an array of complexes to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.complex64)
        if length is None: length = buf.size
        ll.hwritec (self.itno, buf, offset, length)

__all__ += ['DataSet', 'DataItem']

class UserDataSet (DataSet):
    def __init__ (self, refobj, create=False):
        if create: mode = 'new'
        else: mode = 'old'

        self.tno = ll.hopen (refobj.base, mode)
        self.refobj = refobj
        self.name = refobj.base
        
    def _close (self):
        ll.hclose (self.tno)

__all__ += ['UserDataSet']

class UVDataSet (DataSet):
    def __init__ (self, refobj, mode):
        # Technically, 'old' mode is read-only with regard to the
        # UV data, but you can still write non-UV header variables.
        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        elif mode == 'a': modestr = 'append'
        else: raise ValueError ('Unsupported mode "%s"; "rw", "c", and "a" are allowed' % mode)

        self.tno = ll.uvopen (refobj.base, modestr)
        self.refobj = refobj
        self.name = refobj.base

    def _close (self):
        ll.uvclose (self.tno)

    # These override the basic DataSet operations

    def flush (self):
        """Write out any unbuffered changes to the UV data set."""
        
        self._checkOpen ()
        ll.uvflush (self.tno)

    # UV-specific operations

    def next (self):
        """Skip to the next UV data record. On write, this causes an
        end-of-record mark to be written."""

        self._checkOpen ()
        ll.uvnext (self.tno)

    def rewind (self):
        """Rewind to the beginning of the file, allowing the UV data to
        be reread from the start."""

        self._checkOpen ()
        ll.uvrewind (self.tno)

    def lowlevelRead (self, preamble, data, flags, length=None):
        """Read a visibility record from the file. This function should
        be avoided in favor of the uvdat routines except for certain
        low-level manipulations. Length defaults to the length of the
        flags array.

        Returns: the number of items read."""

        if length is None: length = flags.size

        self._checkOpen ()
        return ll.uvread (self.tno, preamble, data, flags, length)
    
    def write (self, preamble, data, flags, length=None):
        """Write a visibility record consisting of the given preamble,
        data, flags, and length. Length defaults to the length of the
        flags array."""

        if length is None: length = flags.size

        self._checkOpen ()
        ll.uvwrite (self.tno, preamble, data, flags, length)

    def rewriteFlags (self, flags):
        """Rewrite the channel flagging data for the current
        visibility record. 'flags' should be a 1D integer ndarray of the
        same length and dtype returned by a uvread call."""

        self._checkOpen ()
        ll.uvflgwr (self.tno, flags)
        
    # uvset exploders

    def _uvset (self, object, type, n, p1, p2, p3):
        self._checkOpen ()
        ll.uvset (self.tno, object, type, n, p1, p2, p3)

    def setPreambleType (self, *vars):
        """Specify up to five variables to put in the preamble block.
        Should be given a list of variable names; 'uv' and 'uvw' are
        a special expansion of 'coord' that expand out to their
        respective UV coordinates. Default list is 'uvw', 'time',
        'baseline'."""
        
        self._uvset ('preamble', '/'.join (vars), 0, 0., 0., 0.)

    def setSelectAmplitude (self, selamp):
        """Specify whether selection based on amplitude should be
        performed."""

        if selamp: val = 1
        else: val = 0
        
        self._uvset ("selection", "amplitude", val, 0., 0., 0.,)
        
    def setSelectWindow (self, selwin):
        """Specify whether selection based on window should be
        performed."""

        if selwin: val = 1
        else: val = 0
        
        self._uvset ("selection", "window", val, 0., 0., 0.,)

    def setPlanetParams (self, major, minor, angle):
        """Set the reference parameters for planet scaling and
        rotation."""

        self._uvset ("planet", "", 0, major, minor, angle)
    
    def setWavelengthMode (self, wlmode):
        """Specify that UV coordinates should be returned in units
        of wavelength. Otherwise, they are returned in nanoseconds."""

        if wlmode:
            self._uvset ("coord", "wavelength", 0, 0., 0., 0.)
        else:
            self._uvset ("coord", "nanosec", 0, 0., 0., 0.)

    def setCorrelationType (self, type):
        """Set the correlation type that will be used in this
        vis file."""

        self._uvset ("corr", type, 0, 0., 0., 0.)
    
    # oh god there are a bunch more of these: data linetype, refernce
    # linetype, gflag, flags, corr
    
    # Variable handling

    def copyMarkedVars (self, output):
        """Copy variables in this data set to the output data set. Only
        copies those variables which have changed and are marked as
        'copy'."""

        self._checkOpen ()
        ll.uvcopyvr (self.tno, output.tno)

    def updated (self):
        """Return true if any user-specified 'important variables' have
        been updated in the last chunk of data read."""

        self._checkOpen ()
        return bool (ll.uvupdate (self.tno))

    def initVarsAsInput (self, linetype):
        """Initialize the UV reading functions to copy variables from
        this file as an input file. Linetype should be one of 'channel',
        'wide', or 'velocity'. Maps to Miriad's varinit() call."""

        self._checkOpen ()
        ll.varinit (self.tno, linetype)

    def initVarsAsOutput (self, input, linetype):
        """Initialize this dataset as the output file for the UV
        reading functions. Linetype should be one of 'channel', 'wide',
        or 'velocity'. Maps to Miriad's varonit() call."""

        self._checkOpen ()
        ll.varonit (input.tno, self.tno, linetype)

    def copyLineVars (self, output):
        """Copy UV variables to the output dataset that describe the
        current line in the input set."""

        self._checkOpen ()
        ll.varcopy (self.tno, output.tno)

    def makeVarTracker (self):
        """Create a UVVarTracker object, which can be used to track
        the values of UV variables and when they change."""
        
        return UVVarTracker (self)

    def probeVar (self, varname):
        """Get information about a given variable. Returns (type, length,
        updated) or None if the variable is undefined.

        type - The variable type character: a (text), r ("real"/float),
        i (int), d (double), c (complex)

        length - The number of elements in this variable; zero if unknown.

        updated - True if the variable was updated on the last UV data read.
        """

        self._checkOpen ()
        (type, length, updated) = ll.uvprobvr (self.tno, varname)

        if type == '' or type == ' ': return None
        return (type, length, updated)

    def getVarString (self, varname):
        """Retrieve the current value of a string-valued UV
        variable. Maximum length of 512 characters."""

        self._checkOpen ()
        return ll.uvgetvra (self.tno, varname)
    
    def getVarInt (self, varname, n=1):
        """Retrieve the current value or values of an int-valued UV
        variable."""

        self._checkOpen ()
        ret = ll.uvgetvri (self.tno, varname, n)

        if n == 1: return ret[0]
        return N.asarray (ret, dtype=N.int)
        
    def getVarFloat (self, varname, n=1):
        """Retrieve the current value or values of a float-valued UV
        variable."""

        self._checkOpen ()
        ret = ll.uvgetvrr (self.tno, varname, n)

        if n == 1: return ret[0]
        return N.asarray (ret, dtype=N.float32)

    def getVarDouble (self, varname, n=1):
        """Retrieve the current value or values of a double-valued UV
        variable."""

        self._checkOpen ()
        ret = ll.uvgetvrd (self.tno, varname, n)
    
        if n == 1: return ret[0]
        return N.asarray (ret, dtype=N.float64)

    def getVarComplex (self, varname, n=1):
        """Retrieve the current value or values of a complex-valued UV
        variable."""

        self._checkOpen ()
        ret = ll.uvgetvrc (self.tno, varname, n)
    
        if n == 1: return ret[0]
        return N.asarray (ret, dtype=N.complex64)

    def getVarFirstString (self, varname, dflt):
        """Retrieve the first value of a string-valued UV
        variable with a default if the variable is not present.
        Maximum length of 512 characters."""

        self._checkOpen ()
        return ll.uvrdvra (self.tno, varname, dflt)
    
    def getVarFirstInt (self, varname, dflt):
        """Retrieve the first value of an int-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return ll.uvrdvri (self.tno, varname, dflt)
    
    def getVarFirstFloat (self, varname, dflt):
        """Retrieve the first value of a float-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return ll.uvrdvrr (self.tno, varname, dflt)
    
    def getVarFirstDouble (self, varname, dflt):
        """Retrieve the first value of a double-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return ll.uvrdvrd (self.tno, varname, dflt)
    
    def getVarFirstComplex (self, varname, dflt):
        """Retrieve the first value of a complex-valued UV
        variable with a default if the variable is not present."""

        dflt = complex (dflt)
        self._checkOpen ()
        retval = ll.uvrdvrd (self.tno, varname, (dflt.real, dflt.imag))
        return complex (retval[0], retval[1])
    
    def trackVar (self, varname, watch, copy):
        """Set how the given variable is tracked. If 'watch' is true, updated()
        will return true when this variable changes after a chunk of UV data
        is read. If 'copy' is true, this variable will be copied when
        copyMarkedVars() is called.
        """

        switches = ''
        if watch: switches += 'u'
        if copy: switches += 'c'

        self._checkOpen ()
        ll.uvtrack (self.tno, varname, switches)

    def scanUntilChange (self, varname):
        """Scan through the UV data until the given variable changes. Reads
        to the end of the record in which the variable changes. Returns False
        if end-of-file was reached, True otherwise."""

        self._checkOpen ()
        return ll.uvscan (self.tno, varname) == 0

    def writeVarInt (self, name, val):
        """Write an integer UV variable. val can either be a single value or
        an ndarray for array variables."""
        
        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.int32)
            v2[0] = int (val)
            val = v2

        ll.uvputvri (self.tno, name, val)
    
    def writeVarFloat (self, name, val):
        """Write an float UV variable. val can either be a single value or
        an ndarray for array variables."""
        
        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.float32)
            v2[0] = float (val)
            val = v2

        ll.uvputvrr (self.tno, name, val)
    
    def writeVarDouble (self, name, val):
        """Write a double UV variable. val can either be a single value or
        an ndarray for array variables."""
        
        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.float64)
            v2[0] = float (val)
            val = v2

        ll.uvputvrd (self.tno, name, val)
    
class UVVarTracker (object):
    def __init__ (self, owner):
        self.dataset = owner
        self.refobj = owner.refobj
        self.vhnd = ll.uvvarini (owner.tno)

    def track (self, *vars):
        """Indicate that the specifieds variable should be tracked by this
        tracker."""

        for var in vars:
            ll.uvvarset (self.vhnd, var)

    def copyTo (self, output):
        """Copy the variables tracked by this tracker into the output
        data set."""

        ll.uvvarcpy (self.vhnd, output.tno)

    def updated (self):
        """Return true if one of the variables tracked by this tracker
        was updated in the last UV data read."""

        return bool (ll.uvvarupd (self.vhnd))

__all__ += ['UVDataSet', 'UVVarTracker']

MASK_MODE_FLAGS = 1
MASK_MODE_RUNS = 2
_maskModes = set ((MASK_MODE_FLAGS, MASK_MODE_RUNS))

class MaskItem (object):
    """A 'mask' item contained within a Miriad dataset."""

    def __init__ (self, dataset, keyword, mode):
        self.dataset = dataset
        self.refobj = dataset.refobj
        self.name = keyword
        self.handle = None

        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.handle = ll.mkopen (dataset.tno, keyword, modestr)


    def read (self, mode, flags, offset, n):
        if mode not in _maskModes:
            raise ValueError ('Unexpected mask mode %d' % mode)
        self._checkOpen ()
        return ll.mkread (self.handle, mode, flags, offset, n)


    def write (self, mode, flags, offset, n=None):
        if mode not in _maskModes:
            raise ValueError ('Unexpected mask mode %d' % mode)
        if n is None:
            n = flags.size
        self._checkOpen ()
        ll.mkwrite (self.handle, mode, flags, offset, n)


    def flush (self):
        self._checkOpen ()
        ll.mkflush (self.handle)


    def close (self):
        self._checkOpen ()
        ll.mkclose (self.handle)
        self.handle = None


    def isOpen (self):
        return self.handle is not None


    def _checkOpen (self):
        if self.handle is not None:
            return
        raise RuntimeError ('Illegal operation on a closed mask item')


    def __del__ (self):
        if ll is None or self.handle is None:
            return

        self.close ()


__all__ += ['MaskItem', 'MASK_MODE_FLAGS', 'MASK_MODE_RUNS']
