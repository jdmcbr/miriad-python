"""Miscellaneous utility MIRIAD subroutines."""

import lowlevel as ll
import numpy as N

# Banner printing (and Id string decoding)

def printBannerSvn (name, desc, idstr):
    """Print a banner string containing the name of a task, its
    description, and versioning information extracted from a
    Subversion ID string. The banner string is returned as well."""

    file, rev, date, time, user = idstr[5:-2].split ()
    
    b = '%s: %s (Python, SVN r%s, modified %s %s)' % (name.upper (), desc,
                                                      rev, date, time)
    print b
    return b

# Baseline-related stuff

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return ll.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return ll.antbas (ant1, ant2)

# Polarizations. From subs/uvdat.h

POL_II = 0
POL_I = 1
POL_Q = 2
POL_U = 3
POL_V = 4
POL_RR = -1
POL_LL = -2
POL_RL = -3
POL_LR = -4
POL_XX = -5
POL_YY = -6
POL_XY = -7
POL_YX = -8
POL_QQ = 5
POL_UU = 6

_polNames = { POL_II: 'II', POL_I: 'I', POL_Q: 'Q',
              POL_U: 'U', POL_V: 'V', POL_RR: 'RR',
              POL_LL: 'LL', POL_RL: 'RL', POL_LR: 'LR',
              POL_XX: 'XX', POL_YY: 'YY', POL_XY: 'XY',
              POL_YX: 'YX', POL_QQ: 'QQ', POL_UU: 'UU' }

def polarizationName (polnum):
    """Return the textual description of a MIRIAD polarization type
    from its number."""

    return _polNames[polnum]

def polarizationNumber (polname):
    for (num, name) in _polNames.iteritems ():
        if name.lower () == polname.lower (): return num

    raise Exception ('Unknown polarization name \'%s\'' % polname)

def polarizationIsInten (polnum):
    """Return True if the given polarization is intensity-type, e.g.,
    is I, XX, YY, RR, or LL."""
    
    return ll.polspara (polnum)

# And, merging them together: antpol and basepol handling.
#
# In the following, "M" stands for the MIRIAD antenna number
# of an antenna. These numbers are 1-based. "P" stands for
# a MIRIAD polarization number, values given above.
#
# First, a "feed polarization" (f-pol) is a polarization that an
# individual feed can respond to. I am pretty sure that all or some of
# the I, Q, U, V values given below are inappropriate, but I do
# think MIRIAD can work with UV datasets given in Stokes parameters,
# so for completeness we include them here, even if there can't be
# a physical feed that corresponds to such an entity.

FPOL_X = 0
FPOL_Y = 1
FPOL_R = 2
FPOL_L = 3
FPOL_I = 4
FPOL_Q = 5
FPOL_U = 6
FPOL_V = 7

fPolNames = 'XYRLIQUV'

# This table helps split a MIRIAD/FITS pol code into a pair of f-pol values.
# The pair is packed into 8 bits, the upper 3 being for the left pol
# and the lower 4 being for the right. If the high bit is 1, the pol code
# cannot legally be split. An offset of 8 is required because the pol codes range
# from -8 to +6

_polToFPol = [0x10, 0x01, 0x11, 0x00, # YX XY YY XX
              0x32, 0x23, 0x33, 0x22, # LR RL LL RR
              0x44, # II
              0x80, 0x80, 0x80, 0x80, # I Q U V
              0x55, 0x66] # QQ UU

# This table performs the reverse mapping, with index being the two
# f-pol values packed into four bits each. A value of 99 indicates
# an illegal pairing.

_fpolToPol = N.ndarray (128, dtype=N.int)
_fpolToPol.fill (99)
_fpolToPol[0x00] = POL_XX
_fpolToPol[0x01] = POL_XY
_fpolToPol[0x10] = POL_YX
_fpolToPol[0x11] = POL_YY
_fpolToPol[0x22] = POL_RR
_fpolToPol[0x23] = POL_RL
_fpolToPol[0x32] = POL_LR
_fpolToPol[0x33] = POL_LL
_fpolToPol[0x44] = POL_II
_fpolToPol[0x55] = POL_QQ
_fpolToPol[0x66] = POL_UU

# A "antpol" (AP) is a >=8-bit integer identifying an
# antenna/feed-polarization combination. It can be decoded without any
# external information.  The translation between AP and M,FP is:
#
#   AP = (M - 1) << 3 + FP
#
# or
#
#   M = AP >> 3 + 1
#   P = AP & 0x7
#
# Note that arbitrarily-large antenna numbers can be encoded
# if sufficiently many bits are used to store the AP.

def fmtAP (ap):
    m = (ap >> 3) + 1
    fp = ap & 0x7
    return '%d%c' % (m, fPolNames[fp])

def apAnt (ap):
    return (ap >> 3) + 1

def apFPol (ap):
    return ap & 0x7

def antpol2ap (m, fpol):
    return ((m - 1) << 3) + fpol

def parseAP (text):
    try:
        polcode = text[-1].upper ()
        fpol = fPolNames.find (polcode)
        assert fpol >= 0

        m = int (text[:-1])
        assert m > 0
    except:
        raise Exception ('Text does not encode a valid AP: ' + text)

    return antpol2ap (m, fpol)

# A "basepol" is a baseline between two antpols. It can be encoded as
# a pair of antpols.

def fmtAPs (pair):
    ap1, ap2 = pair

    m1 = (ap1 >> 3) + 1
    fp1 = ap1 & 0x7
    m2 = (ap2 >> 3) + 1
    fp2 = ap2 & 0x7

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])

def aps2ants (pair):
    """Converts a tuple of two APs into a tuple of (ant1, ant2, pol)."""

    ap1, ap2 = pair
    m1 = (ap1 >> 3) + 1
    m2 = (ap2 >> 3) + 1
    assert m1 > 0, 'Illegal AP value: m1 <= 0'
    assert m1 <= m2, 'Illegal AP value: m1 > m2'

    idx = ((ap1 & 0x7) << 4) + (ap2 & 0x7)
    pol = _fpolToPol[idx]
    assert pol != 99, 'AP value represents illegal polarization pairing'

    return (m1, m2, pol)

def aps2blpol (pair):
    """Converts a tuple of two APs into a tuple of (bl, pol) where
'bl' is the MIRIAD-encoded baseline number."""

    m1, m2, pol = aps2ants (pair)
    return (encodeBaseline (m1, m2), pol)

def mir2aps (inp, preamble):
    """Uses a UV dataset and a preamble array to return a tuple of
(ap1, ap2)."""

    pol = inp.getVarInt ('pol')
    fps = _polToFPol[pol + 8]
    assert (fps & 0x80) == 0, 'Un-breakable polarization code'

    m1, m2 = ll.basants (preamble[4], True)

    ap1 = ((m1 - 1) << 3) + ((fps >> 4) & 0x07)
    ap2 = ((m2 - 1) << 3) + (fps & 0x07)

    return ap1, ap2

def apsAreInten (pair):
    ap1, ap2 = pair
    return ap1 & 0x7 == ap2 & 0x7

# A "32-bit basepol" (BP32) encodes a basepol in a single >=32-bit
# integer. It can be decoded without any external information. The
# translation between BP32 and M1,M2,FP1,FP2 is:
#
#  BP32 = ((M1 - 1) << 19) + (FP1 << 16) + ((M2 - 1) << 3) + FP2
#
# or
#
#  M1 = (BP32 >> 19) + 1
#  FP1 = (BP32 >> 16) & 0x7
#  M2 = (BP32 >> 3 & 0x1FFF) + 1
#  FP2 = BP32 & 0x7
#
# This encoding allocates 13 bits for antenna number, which gets us up
# to 4096 antennas. This should be sufficient for most applications.

def fmtBP (bp32):
    m1 = ((bp32 >> 19) & 0x1FFF) + 1
    fp1 = (bp32 >> 16) & 0x7
    m2 = ((bp32 >> 3) & 0x1FFF) + 1
    fp2 = bp32 & 0x7

    assert m1 > 0, 'Illegal BP32 in fmtBP: m1 <= 0'
    assert m2 >= m1, 'Illegal BP32 in fmtBP: m1 > m2'

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])

def mir2bp (inp, preamble):
    pol = inp.getVarInt ('pol')
    fps = _polToFPol[pol + 8]
    assert (fps & 0x80) == 0, 'Un-breakable polarization code'

    m1, m2 = ll.basants (preamble[4], True)
    
    return ((m1 - 1) << 19) + ((fps & 0x70) << 12) + ((m2 - 1) << 3) \
        + (fps & 0x7)

def bp2aps (bp32):
    return ((bp32 >> 16) & 0xFFFF, bp32 & 0xFFFF)

def aps2bp (pair):
    ap1, ap2 = pair

    assert (ap1 >> 3) >= 0, 'Illegal baseline pairing: m1 < 0'
    assert (ap1 >> 3) <= (ap2 >> 3), 'Illegal baseline pairing: m1 > m2'
    assert ap2 <= 0xFFFF, 'Antnum too high to be encoded in BP32'

    return (ap1 << 16) + (ap2 & 0xFFFF)

def bpIsInten (bp32):
    return ((bp32 >> 16) & 0x7) == bp32 & 0x7

def parseBP (text):
    t1, t2 = text.split ('-', 1)

    try:
        polcode = t1[-1].upper ()
        fp1 = fPolNames.find (polcode)
        assert fp1 >= 0

        m1 = int (t1[:-1])

        polcode = t2[-1].upper ()
        fp2 = fPolNames.find (polcode)
        assert fp2 >= 0

        m2 = int (t2[:-1])

        assert m1 > 0
        assert m1 <= m2
    except:
        raise Exception ('Text does not encode a valid BP: ' + text)

    return ((m1 - 1) << 19) + (fp1 << 12) + ((m2 - 1) << 3) + fp2

# FIXME: following not implemented. Not sure if it is actually
# necessary since in practice we condense down lists of basepols into
# customized arrays, since a basepol might be missing.

# An "local antpol" (LAP) encodes the same information as a AP, but can only
# encode two possible polarizations. This means that external
# information is needed to decode an AP, but that it can be used to
# index into arrays efficiently (assuming a full-pol correlator
# that doesn't skip many MIRIAD antenna numbers). The assumption is that
# a set of antpols will include FPs of X & Y or R & L. In the former case
# the "reference feed polarzation" (RFP) is X; in the latter it is R.
#
# The translation between AP, RFP and M, FP is:
#
#  AP = (M - 1) << 1 + (FP - RFP)
#
# or
#
#  M = (AP >> 1) + 1
#  FP = (AP & 0x1) + RFP



# Date stuff

def jdToFull (jd):
    """Return a string representing the given Julian date as date
    and time of the form 'YYMMDD:HH:MM:SS.S'."""
    return ll.julday (jd, 'H')

def jdToPartial (jd):
    """Return a string representing the time-of-day portion of the
    given Julian date in the form 'HH:MM:SS'. Obviously, this loses
    precision from the JD representation."""

    # smauvplt does the hr/min/sec breakdown manually so I shall
    # do the same except maybe a bit better because I use jul2ut.

    from math import floor, pi
    fullhrs = ll.jul2ut (jd) * 12 / pi

    hr = int (floor (fullhrs))
    mn = int (floor (60 * (fullhrs - hr)))
    sc = int (3600 * (fullhrs - hr - mn / 60.))

    return '%02d:%02d:%02d' % (hr, mn, sc)

def dateOrTimeToJD (calendar):
    """Return a full or offset Julian date parsed from the argument.
(An offset Julian date is between 0 and 1 and measures a time of day.
The anchor point to which the offset Julian date is relative to is
irrelevant to this function.) Acceptable input formats are:

  yymmmdd.dd (D)
  dd/mm/yy (F)
  [yymmmdd:][hh[:mm[:ss.s]]] (H)
  ccyy-mm-dd[Thh[:mm[:ss.ss]]] (T)
  dd-mm-ccyy

See the documentation to Miriad function DAYJUL for a more detailed
description of the parser behavior. The returned Julian date is of
moderate accuracy only, e.g. good to a few seconds (I think?)."""

    return ll.dayjul (calendar)
