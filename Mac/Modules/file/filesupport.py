# This script generates a Python interface for an Apple Macintosh Manager.
# It uses the "bgen" package to generate C code.
# The function specifications are generated by scanning the mamager's header file,
# using the "scantools" package (customized for this particular manager).
#
# XXXX TO DO:
# - Implement correct missing FSSpec handling for Alias methods
# - Implement FInfo

import string

# Declarations that change for each manager
#MACHEADERFILE = 'Files.h'		# The Apple header file
MODNAME = '_File'				# The name of the module
LONGMODNAME = 'Carbon.File'		# The "normal" external name of the module

# The following is *usually* unchanged but may still require tuning
MODPREFIX = 'File'			# The prefix for module-wide routines
INPUTFILE = string.lower(MODPREFIX) + 'gen.py' # The file generated by the scanner
OUTPUTFILE = MODNAME + "module.c"	# The file generated by this program

from macsupport import *

# Various integers:
SInt64 = Type("SInt64", "L")
UInt64 = Type("UInt64", "L")
FNMessage = Type("FNMessage", "l")
FSAllocationFlags = Type("FSAllocationFlags", "H")
FSCatalogInfoBitmap = Type("FSCatalogInfoBitmap", "l")
FSIteratorFlags = Type("FSIteratorFlags", "l")
FSVolumeRefNum = Type("FSVolumeRefNum", "h")
AliasInfoType = Type("AliasInfoType", "h")

# Various types of strings:
#class UniCharCountBuffer(InputOnlyType):
#	pass
class VarReverseInputBufferType(ReverseInputBufferMixin, VarInputBufferType):
	pass
FullPathName = VarReverseInputBufferType()
ConstStr31Param = OpaqueArrayType("Str31", "PyMac_BuildStr255", "PyMac_GetStr255")
ConstStr32Param = OpaqueArrayType("Str32", "PyMac_BuildStr255", "PyMac_GetStr255")
ConstStr63Param = OpaqueArrayType("Str63", "PyMac_BuildStr255", "PyMac_GetStr255")
Str63 = OpaqueArrayType("Str63", "PyMac_BuildStr255", "PyMac_GetStr255")

HFSUniStr255 = OpaqueType("HFSUniStr255", "PyMac_BuildHFSUniStr255", "PyMac_GetHFSUniStr255")
UInt8_ptr = InputOnlyType("UInt8 *", "s")

# Other types:
class OptionalFSxxxType(OpaqueByValueType):
	def declare(self, name):
		Output("%s %s__buf__;", self.typeName, name)
		Output("%s *%s = &%s__buf__;", self.typeName, name, name)
	
FInfo = OpaqueByValueStructType("FInfo", "PyMac_BuildFInfo", "PyMac_GetFInfo")
FInfo_ptr = OpaqueType("FInfo", "PyMac_BuildFInfo", "PyMac_GetFInfo")
AliasHandle = OpaqueByValueType("AliasHandle", "Alias")
FSSpec = OpaqueType("FSSpec", "FSSpec")
FSSpec_ptr = OpaqueType("FSSpec", "FSSpec")
OptFSSpecPtr = OptionalFSxxxType("FSSpec", "BUG", "myPyMac_GetOptFSSpecPtr")
FSRef = OpaqueType("FSRef", "FSRef")
FSRef_ptr = OpaqueType("FSRef", "FSRef")
OptFSRefPtr = OptionalFSxxxType("FSRef", "BUG", "myPyMac_GetOptFSRefPtr")

# To be done:
#CatPositionRec
#FSCatalogInfo
#FSForkInfo
#FSIterator
#FSVolumeInfo
#FSSpecArrayPtr

includestuff = includestuff + """
#ifdef WITHOUT_FRAMEWORKS
#include <Files.h>
#else
#include <Carbon/Carbon.h>
#endif

/* Forward declarations */
extern PyObject *FSRef_New(FSRef *itself);
extern PyObject *FSSpec_New(FSSpec *itself);
extern PyObject *Alias_New(AliasHandle itself);
extern int FSRef_Convert(PyObject *v, FSRef *p_itself);
extern int FSSpec_Convert(PyObject *v, FSSpec *p_itself);
extern int Alias_Convert(PyObject *v, AliasHandle *p_itself);
static int myPyMac_GetFSSpec(PyObject *v, FSSpec *spec);
static int myPyMac_GetFSRef(PyObject *v, FSRef *fsr);

/*
** Optional fsspec and fsref pointers. None will pass NULL
*/
static int
myPyMac_GetOptFSSpecPtr(PyObject *v, FSSpec **spec)
{
	if (v == Py_None) {
		*spec = NULL;
		return 1;
	}
	return myPyMac_GetFSSpec(v, *spec);
}

static int
myPyMac_GetOptFSRefPtr(PyObject *v, FSRef **ref)
{
	if (v == Py_None) {
		*ref = NULL;
		return 1;
	}
	return myPyMac_GetFSRef(v, *ref);
}

/*
** Parse/generate objsect
*/
static PyObject *
PyMac_BuildHFSUniStr255(HFSUniStr255 *itself)
{

	return Py_BuildValue("u#", itself->unicode, itself->length);
}

/*
** Parse/generate objsect
*/
static PyObject *
PyMac_BuildFInfo(FInfo *itself)
{

	return Py_BuildValue("O&O&HO&h",
		PyMac_BuildOSType, itself->fdType,
		PyMac_BuildOSType, itself->fdCreator,
		itself->fdFlags,
		PyMac_BuildPoint, &itself->fdLocation,
		itself->fdFldr);
}

static int
PyMac_GetFInfo(PyObject *v, FInfo *itself)
{
	return PyArg_ParseTuple(v, "O&O&HO&h",
		PyMac_GetOSType, &itself->fdType,
		PyMac_GetOSType, &itself->fdCreator,
		&itself->fdFlags,
		PyMac_GetPoint, &itself->fdLocation,
		&itself->fdFldr);
}
"""

finalstuff = finalstuff + """
static int
myPyMac_GetFSSpec(PyObject *v, FSSpec *spec)
{
	Str255 path;
	short refnum;
	long parid;
	OSErr err;
	FSRef fsr;

	if (FSSpec_Check(v)) {
		*spec = ((FSSpecObject *)v)->ob_itself;
		return 1;
	}

	if (PyArg_Parse(v, "(hlO&)",
						&refnum, &parid, PyMac_GetStr255, &path)) {
		err = FSMakeFSSpec(refnum, parid, path, spec);
		if ( err && err != fnfErr ) {
			PyMac_Error(err);
			return 0;
		}
		return 1;
	}
	PyErr_Clear();
#if !TARGET_API_MAC_OSX
	/* On OS9 we now try a pathname */
	if ( PyString_Check(v) ) {
		/* It's a pathname */
		if( !PyArg_Parse(v, "O&", PyMac_GetStr255, &path) )
			return 0;
		refnum = 0; /* XXXX Should get CurWD here?? */
		parid = 0;
		err = FSMakeFSSpec(refnum, parid, path, spec);
		if ( err && err != fnfErr ) {
			PyMac_Error(err);
			return 0;
		}
		return 1;
	}
	PyErr_Clear();
#endif
	/* Otherwise we try to go via an FSRef. On OSX we go all the way,
	** on OS9 we accept only a real FSRef object
	*/
#if TARGET_API_MAC_OSX
	if ( myPyMac_GetFSRef(v, &fsr) ) {
#else
	if ( PyArg_Parse(v, "O&", FSRef_Convert, &fsr) ) {
#endif	
		err = FSGetCatalogInfo(&fsr, kFSCatInfoNone, NULL, NULL, spec, NULL);
		if (err != noErr) {
			PyMac_Error(err);
			return 0;
		}
		return 1;
	}
	PyErr_SetString(PyExc_TypeError, "FSSpec, FSRef, pathname or (refnum, parid, path) required");
	return 0;
}

static int
myPyMac_GetFSRef(PyObject *v, FSRef *fsr)
{
	OSStatus err;
	
	if (FSRef_Check(v)) {
		*fsr = ((FSRefObject *)v)->ob_itself;
		return 1;
	}

#if TARGET_API_MAC_OSX
	/* On OSX we now try a pathname */
	if ( PyString_Check(v) ) {
		if ( (err=FSPathMakeRef(PyString_AsString(v), fsr, NULL)) ) {
			PyMac_Error(err);
			return 0;
		}
		return 1;
	}
	/* XXXX Should try unicode here too */
#endif
	/* Otherwise we try to go via an FSSpec */
	if (FSSpec_Check(v)) {
		if ((err=FSpMakeFSRef(&((FSSpecObject *)v)->ob_itself, fsr)) == 0)
			return 1;
		PyMac_Error(err);
		return 0;
	}
	PyErr_SetString(PyExc_TypeError, "FSRef, FSSpec or pathname required");
	return 0;
}

"""

execfile(string.lower(MODPREFIX) + 'typetest.py')

# Our object types:
class FSSpecDefinition(PEP253Mixin, GlobalObjectDefinition):
	getsetlist = [
		("data",
		 "return PyString_FromStringAndSize((char *)&self->ob_itself, sizeof(self->ob_itself));",
		 None,
		 "Raw data of the FSSpec object"
		)
	]
		 
	def __init__(self, name, prefix, itselftype):
		GlobalObjectDefinition.__init__(self, name, prefix, itselftype)
		self.argref = "*"	# Store FSSpecs, but pass them by address

	def outputCheckNewArg(self):
		Output("if (itself == NULL) return PyMac_Error(resNotFound);")

	def output_tp_newBody(self):
		Output("PyObject *self;");
		Output()
		Output("if ((self = type->tp_alloc(type, 0)) == NULL) return NULL;")
		Output("memset(&((%s *)self)->ob_itself, 0, sizeof(%s));", 
			self.objecttype, self.objecttype)
		Output("return self;")

	def output_tp_initBody(self):
		Output("PyObject *v = NULL;")
		Output("char *rawdata = NULL;")
		Output("int rawdatalen = 0;")
		Output("char *kw[] = {\"itself\", \"rawdata\", 0};")
		Output()
		Output("if (!PyArg_ParseTupleAndKeywords(args, kwds, \"|Os#\", kw, &v, &rawdata, &rawdatalen))")
		Output("return -1;")
		Output("if (v && rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"Only one of itself or rawdata may be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (!v && !rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"One of itself or rawdata must be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (rawdata)")
		OutLbrace()
		Output("if (rawdatalen != sizeof(%s))", self.itselftype)
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"%s rawdata incorrect size\");",
			self.itselftype)
		Output("return -1;")
		OutRbrace()
		Output("memcpy(&((%s *)self)->ob_itself, rawdata, rawdatalen);", self.objecttype)
		Output("return 0;")
		OutRbrace()
		Output("if (myPyMac_GetFSSpec(v, &((%s *)self)->ob_itself)) return 0;", self.objecttype)
		Output("return -1;")
	
	def outputRepr(self):
		Output()
		Output("static PyObject * %s_repr(%s *self)", self.prefix, self.objecttype)
		OutLbrace()
		Output("char buf[512];")
		Output("""PyOS_snprintf(buf, sizeof(buf), \"%%s((%%d, %%ld, '%%.*s'))\",
		self->ob_type->tp_name,
		self->ob_itself.vRefNum, 
		self->ob_itself.parID,
		self->ob_itself.name[0], self->ob_itself.name+1);""")
		Output("return PyString_FromString(buf);")
		OutRbrace()
		
class FSRefDefinition(PEP253Mixin, GlobalObjectDefinition):
	getsetlist = [
		("data",
		 "return PyString_FromStringAndSize((char *)&self->ob_itself, sizeof(self->ob_itself));",
		 None,
		 "Raw data of the FSRef object"
		)
	]
		 
	def __init__(self, name, prefix, itselftype):
		GlobalObjectDefinition.__init__(self, name, prefix, itselftype)
		self.argref = "*"	# Store FSRefs, but pass them by address

	def outputCheckNewArg(self):
		Output("if (itself == NULL) return PyMac_Error(resNotFound);")

	def output_tp_newBody(self):
		Output("PyObject *self;");
		Output()
		Output("if ((self = type->tp_alloc(type, 0)) == NULL) return NULL;")
		Output("memset(&((%s *)self)->ob_itself, 0, sizeof(%s));", 
			self.objecttype, self.objecttype)
		Output("return self;")
	
	def output_tp_initBody(self):
		Output("PyObject *v = NULL;")
		Output("char *rawdata = NULL;")
		Output("int rawdatalen = 0;")
		Output("char *kw[] = {\"itself\", \"rawdata\", 0};")
		Output()
		Output("if (!PyArg_ParseTupleAndKeywords(args, kwds, \"|Os#\", kw, &v, &rawdata, &rawdatalen))")
		Output("return -1;")
		Output("if (v && rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"Only one of itself or rawdata may be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (!v && !rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"One of itself or rawdata must be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (rawdata)")
		OutLbrace()
		Output("if (rawdatalen != sizeof(%s))", self.itselftype)
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"%s rawdata incorrect size\");",
			self.itselftype)
		Output("return -1;")
		OutRbrace()
		Output("memcpy(&((%s *)self)->ob_itself, rawdata, rawdatalen);", self.objecttype)
		Output("return 0;")
		OutRbrace()
		Output("if (myPyMac_GetFSRef(v, &((%s *)self)->ob_itself)) return 0;", self.objecttype)
		Output("return -1;")
	
class AliasDefinition(PEP253Mixin, GlobalObjectDefinition):
	# XXXX Should inherit from resource?
	getsetlist = [
		("data",
		 """int size;
			PyObject *rv;
			
			size = GetHandleSize((Handle)self->ob_itself);
			HLock((Handle)self->ob_itself);
			rv = PyString_FromStringAndSize(*(Handle)self->ob_itself, size);
			HUnlock((Handle)self->ob_itself);
			return rv;
		""",
		 None,
		 "Raw data of the alias object"
		)
	]
		 
	def outputCheckNewArg(self):
		Output("if (itself == NULL) return PyMac_Error(resNotFound);")
		
	def outputStructMembers(self):
		GlobalObjectDefinition.outputStructMembers(self)
		Output("void (*ob_freeit)(%s ptr);", self.itselftype)
		
	def outputInitStructMembers(self):
		GlobalObjectDefinition.outputInitStructMembers(self)
		Output("it->ob_freeit = NULL;")
		
	def outputCleanupStructMembers(self):
		Output("if (self->ob_freeit && self->ob_itself)")
		OutLbrace()
		Output("self->ob_freeit(self->ob_itself);")
		OutRbrace()
		Output("self->ob_itself = NULL;")

	def output_tp_newBody(self):
		Output("PyObject *self;");
		Output()
		Output("if ((self = type->tp_alloc(type, 0)) == NULL) return NULL;")
		Output("((%s *)self)->ob_itself = NULL;", self.objecttype)
		Output("return self;")
	
	def output_tp_initBody(self):
		Output("%s itself = NULL;", self.itselftype)
		Output("char *rawdata = NULL;")
		Output("int rawdatalen = 0;")
		Output("Handle h;")
		Output("char *kw[] = {\"itself\", \"rawdata\", 0};")
		Output()
		Output("if (!PyArg_ParseTupleAndKeywords(args, kwds, \"|O&s#\", kw, %s_Convert, &itself, &rawdata, &rawdatalen))",
			self.prefix)
		Output("return -1;")
		Output("if (itself && rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"Only one of itself or rawdata may be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (!itself && !rawdata)")
		OutLbrace()
		Output("PyErr_SetString(PyExc_TypeError, \"One of itself or rawdata must be specified\");")
		Output("return -1;")
		OutRbrace()
		Output("if (rawdata)")
		OutLbrace()
		Output("if ((h = NewHandle(rawdatalen)) == NULL)")
		OutLbrace()
		Output("PyErr_NoMemory();")
		Output("return -1;")
		OutRbrace()
		Output("HLock(h);")
		Output("memcpy((char *)*h, rawdata, rawdatalen);")
		Output("HUnlock(h);")
		Output("((%s *)self)->ob_itself = (%s)h;", self.objecttype, self.itselftype)
		Output("return 0;")
		OutRbrace()
		Output("((%s *)self)->ob_itself = itself;", self.objecttype)
		Output("return 0;")
	
# Alias methods come in two flavors: those with the alias as arg1 and
# those with the alias as arg 2.
class Arg2MethodGenerator(MethodGenerator):
	"""Similar to MethodGenerator, but has self as second argument"""

	def parseArgumentList(self, args):
		args0, arg1, argsrest = args[:1], args[1], args[2:]
		t0, n0, m0 = arg1
		args = args0 + argsrest
		if m0 != InMode:
			raise ValueError, "method's 'self' must be 'InMode'"
		self.itself = Variable(t0, "_self->ob_itself", SelfMode)
		FunctionGenerator.parseArgumentList(self, args)
		self.argumentList.insert(2, self.itself)

# From here on it's basically all boiler plate...

# Create the generator groups and link them
module = MacModule(MODNAME, MODPREFIX, includestuff, finalstuff, initstuff,
	longname=LONGMODNAME)

aliasobject = AliasDefinition('Alias', 'Alias', 'AliasHandle')
fsspecobject = FSSpecDefinition('FSSpec', 'FSSpec', 'FSSpec')
fsrefobject = FSRefDefinition('FSRef', 'FSRef', 'FSRef')

module.addobject(aliasobject)
module.addobject(fsspecobject)
module.addobject(fsrefobject)

# Create the generator classes used to populate the lists
Function = OSErrFunctionGenerator
Method = OSErrMethodGenerator

# Create and populate the lists
functions = []
alias_methods = []
fsref_methods = []
fsspec_methods = []
execfile(INPUTFILE)

# Manual generators:
FSRefMakePath_body = """
OSStatus _err;
#define MAXPATHNAME 1024
UInt8 path[MAXPATHNAME];
UInt32 maxPathSize = MAXPATHNAME;

if (!PyArg_ParseTuple(_args, ""))
	return NULL;
_err = FSRefMakePath(&_self->ob_itself,
					 path,
					 maxPathSize);
if (_err != noErr) return PyMac_Error(_err);
_res = Py_BuildValue("s", path);
return _res;
"""
f = ManualGenerator("FSRefMakePath", FSRefMakePath_body)
f.docstring = lambda: "() -> string"
fsref_methods.append(f)

FSRef_as_pathname_body = """
_res = FSRef_FSRefMakePath(_self, _args);
return _res;
"""
f = ManualGenerator("as_pathname", FSRef_as_pathname_body)
f.docstring = lambda: "() -> string"
fsref_methods.append(f)

FSSpec_as_pathname_body = """
char strbuf[1024];
OSErr err;

if (!PyArg_ParseTuple(_args, ""))
	return NULL;
err = PyMac_GetFullPathname(&_self->ob_itself, strbuf, sizeof(strbuf));
if ( err ) {
	PyMac_Error(err);
	return NULL;
}
_res = PyString_FromString(strbuf);
return _res;
"""
f = ManualGenerator("as_pathname", FSSpec_as_pathname_body)
f.docstring = lambda: "() -> string"
fsspec_methods.append(f)

FSSpec_as_tuple_body = """
if (!PyArg_ParseTuple(_args, ""))
	return NULL;
_res = Py_BuildValue("(iis#)", _self->ob_itself.vRefNum, _self->ob_itself.parID, 
					&_self->ob_itself.name[1], _self->ob_itself.name[0]);
return _res;
"""
f = ManualGenerator("as_tuple", FSSpec_as_tuple_body)
f.docstring = lambda: "() -> (vRefNum, dirID, name)"
fsspec_methods.append(f)


# add the populated lists to the generator groups
# (in a different wordl the scan program would generate this)
for f in functions: module.add(f)
for f in alias_methods: aliasobject.add(f)
for f in fsspec_methods: fsspecobject.add(f)
for f in fsref_methods: fsrefobject.add(f)

# generate output (open the output file as late as possible)
SetOutputFileName(OUTPUTFILE)
module.generate()

