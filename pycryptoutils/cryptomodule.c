// This wraps the PyCrypto module importing.
// It preloads all important native sub modules.

// For built-in sub modules in general, see:
// http://bugs.python.org/issue1644818
// For some discussion about this, see:
// http://mail.python.org/pipermail/python-dev/2012-June/120117.html

#include "Python.h"
#include "Python-ast.h"
#include "pyarena.h"
#include "pythonrun.h"
#include "errcode.h"
#include "marshal.h"
#include "code.h"
#include "compile.h"
#include "eval.h"
#include "osdefs.h"
#include "import.h"
#include "modsupport.h"

// some code taken from Python/import.c

static PyCodeObject *
parse_source_module(const char *pathname, FILE *fp)
{
    PyCodeObject *co = NULL;
    mod_ty mod;
    PyCompilerFlags flags;
    PyArena *arena = PyArena_New();
    if (arena == NULL)
        return NULL;
	
    flags.cf_flags = 0;
	
    mod = PyParser_ASTFromFile(fp, pathname, Py_file_input, 0, 0, &flags,
                               NULL, arena);
    if (mod) {
        co = PyAST_Compile(mod, pathname, NULL, arena);
    }
    PyArena_Free(arena);
    return co;
}

/* Load a source module from a given file and return its module
 object WITH INCREMENTED REFERENCE COUNT.  If there's a matching
 byte-compiled file, use that instead. */

static PyObject*
load_module(char *name, char *pathname, FILE *fp) {
	PyCodeObject* co = parse_source_module(pathname, fp);
	if (co == NULL)
		return NULL;
	if (Py_VerboseFlag)
		PySys_WriteStderr("import %s # from %s\n",
						  name, pathname);
	PyObject* m = PyImport_ExecCodeModuleEx(name, (PyObject *)co, pathname);
	Py_DECREF(co);
	return m;
}

/* Load a package and return its module object WITH INCREMENTED
 REFERENCE COUNT */

static PyObject *
load_package(char *name, char *pathname)
{
    PyObject *m, *d;
    PyObject *file = NULL;
    PyObject *path = NULL;
    int err;
    char buf[MAXPATHLEN+1];
    FILE *fp = NULL;
	
    m = PyImport_AddModule(name);
    if (m == NULL)
        return NULL;
    if (Py_VerboseFlag)
        PySys_WriteStderr("import %s # directory %s\n",
						  name, pathname);
    d = PyModule_GetDict(m);
    file = PyString_FromString(pathname);
    if (file == NULL)
        goto error;
    path = Py_BuildValue("[O]", file);
    if (path == NULL)
        goto error;
    err = PyDict_SetItemString(d, "__file__", file);
    if (err == 0)
        err = PyDict_SetItemString(d, "__path__", path);
    if (err != 0)
        goto error;
    buf[0] = '\0';
	strcpy(buf, pathname);
	strcat(buf, "/__init__.py");
	fp = fopen(buf, "r");
    m = load_module(name, buf, fp);
    if (fp != NULL)
        fclose(fp);
    goto cleanup;
	
error:
    m = NULL;
cleanup:
    Py_XDECREF(path);
    Py_XDECREF(file);
    return m;
}


extern PyMODINIT_FUNC init_counter(void);
extern PyMODINIT_FUNC init_AES(void);
extern PyMODINIT_FUNC initstrxor(void);

static void importFromStaticallyLinked(char* modName, PyMODINIT_FUNC (*initfunc)(void)) {
	char* subModName = strdup(modName);
	char* shortModName = subModName;
	char* p = strrchr(subModName, '.');
	if(p) {
		*p = 0;
		shortModName = p + 1;
	}

	{
		char* oldcontext = _Py_PackageContext;
		_Py_PackageContext = modName;	
		initfunc();
		_Py_PackageContext = oldcontext;
	}
	
	PyObject* modules = PyImport_GetModuleDict();
	PyObject* m = PyDict_GetItemString(modules, modName);
	if(!m) {
		printf("modName: %s\n", modName);
		Py_FatalError("error loading PyCrypto module (m not found)");
		free(subModName);
		return;
	}
			
	PyObject* subm = PyDict_GetItemString(modules, subModName);
	if(!subm) {
		printf("subModName: %s\n", subModName);
		Py_FatalError("error loading PyCrypto module (subm not found)");
		free(subModName);
		return;
	}

	PyObject* submd = PyModule_GetDict(subm);
	PyDict_SetItemString(submd, shortModName, m);
	
	free(subModName);
}

PyMODINIT_FUNC
init_PyCrypto(void)
{
	char cryptoPath[MAXPATHLEN+1];
	strcpy(cryptoPath, Py_GetProgramFullPath());
	strcat(cryptoPath, "/pylib/otherlibs/Crypto");	
	PyObject* m = load_package("Crypto", cryptoPath);

	if(!PyImport_ImportModule("Crypto.Util"))
		Py_FatalError("failed to load Crypto.Util");
	importFromStaticallyLinked("Crypto.Util._counter", init_counter);
	importFromStaticallyLinked("Crypto.Util.strxor", initstrxor);

	if(!PyImport_ImportModule("Crypto.Cipher"))
		Py_FatalError("failed to load Crypto.Cipher");
	importFromStaticallyLinked("Crypto.Cipher._AES", init_AES);
}
