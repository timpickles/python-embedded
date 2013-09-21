#!/usr/bin/python
import os, sys
os.chdir(os.path.dirname(__file__) or os.getcwd())
import better_exchook
better_exchook.install()

CC = "gcc"
LD = "ld"
LIBTOOL = "libtool"
CFLAGS = []
LDFLAGS = []

buildExec = False

def selectNewestDir(dirpattern):
	from glob import glob
	dirs = glob(dirpattern)
	assert dirs
	# TODO...
	return dirs[-1]
	

# Running in simulator
SIM = True

if True: # iOS
	PLATFORM = 'iPhoneSimulator' if SIM else 'iPhoneOS'
	DEVROOT = "/Applications/Xcode.app/Contents/Developer/Platforms/"+PLATFORM+".platform/Developer"
	#SDKROOT = DEVROOT + "/SDKs/iPhoneOS5.0.sdk"
	SDKROOT = selectNewestDir(DEVROOT + "/SDKs/"+PLATFORM+"*.sdk")
	STATIC_LIB = 'iOS-static-libs/%s-4.3' % ('iPhoneSimulator' if SIM else "iPhoneOS-V7")
	assert os.path.exists(DEVROOT)
	assert os.path.exists(SDKROOT)
	assert os.path.exists(STATIC_LIB)

	# Clang within the Xcode toolchain is buggy?
	# See https://github.com/albertz/playground/blob/master/test-int-cmp.c .
	#CC = DEVROOT + "/usr/bin/arm-apple-darwin10-llvm-gcc-4.2"
	#CC = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/clang"
	CC = DEVROOT + "/usr/bin/gcc"
	LD = DEVROOT + "/usr/bin/ld"
	LIBTOOL = "/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/libtool"
	assert os.path.exists(CC)
	assert os.path.exists(LD)
	assert os.path.exists(LIBTOOL)
	
	CFLAGS += [
		"-isysroot", SDKROOT,
		#"-I%s/usr/lib/gcc/arm-apple-darwin10/4.2.1/include/" % SDKROOT,
		"-I%s/usr/include/" % SDKROOT,
		#"-I/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/lib/clang/3.1/include",
		"-pipe",
		#"-no-cpp-precomp",
		]
	if SIM:
		CFLAGS += ["-arch", "i386",]
	else:
		CFLAGS += [
			"-arch", "armv6",
			"-arch", "armv7",
			]
	CFLAGS += [
		"-miphoneos-version-min=4.3",
		"-mthumb",
		"-g",
		#"-Winvalid-offsetof",
		#"-fmessage-length=0",
		#"-Wno-trigraphs",
		#"-fpascal-strings",
		"-O0",
		"-I%s/include/" % STATIC_LIB,
		]
	LDFLAGS += [
		"-arch", "armv6",
		"-ios_version_min", "4.3",
		#"-isysroot", SDKROOT,
		"-L%s/usr/lib" % SDKROOT,
		"-L%s/usr/lib/system" % SDKROOT,
		"-lc",
		#SDKROOT + "/usr/lib/crt1.o",
		"-lgcc_s.1",
		]
	
PythonDir = "CPython"
assert os.path.exists(PythonDir)

from glob import glob as pyglob
from pprint import pprint
try: os.mkdir("build")
except: pass

def glob(pattern):
	def glob_(baseDir, patternList):
		if not patternList:
			yield baseDir
			return
		head = patternList[0]
		if head == "**":
			for f in glob_(baseDir, patternList[1:]): yield f
			for d in pyglob(baseDir + "/*/"):
				for f in glob_(d, patternList): yield f
			return
		for m in pyglob(baseDir + "/" + head):
			for f in glob_(m, patternList[1:]): yield f
	parts = pattern.split("/")
	if not parts: return
	if parts[0] == "": # start in root
		for f in glob_("/", parts[1:]): yield os.path.normpath(f)
		return
	for f in glob_(".", parts): yield os.path.normpath(f)

baseFiles = \
	set(glob(PythonDir + "/Python/*.c")) - \
	set(glob(PythonDir + "/Python/dynload_*.c")) - \
	set(glob(PythonDir + "/Python/mactoolboxglue.c")) - \
	set(glob(PythonDir + "/Python/sigcheck.c"))
baseFiles |= \
	set(glob(PythonDir + "/Python/dynload_stub.c")) | \
	set(glob("pyimportconfig.c")) | \
	set(glob("pygetpath.c"))

# via blacklist
modFiles = \
	set(glob(PythonDir + "/Modules/**/*.c")) - \
	set(glob(PythonDir + "/Modules/**/testsuite/**/*.c")) - \
	set(glob(PythonDir + "/Modules/_sqlite/**/*.c")) - \
	set(glob(PythonDir + "/Modules/_bsddb.c")) - \
	set(glob(PythonDir + "/Modules/expat/**/*.c")) - \
	set(glob(PythonDir + "/Modules/imgfile.c")) - \
	set(glob(PythonDir + "/Modules/_ctypes/**/*.c")) - \
	set(glob(PythonDir + "/Modules/glmodule.c"))
	# ...
	
# via whitelist
# Add the init reference also to pyimportconfig.c.
# For hacking builtin submodules, see pycryptoutils/cryptomodule.c.
modFiles = \
	set(map(lambda f: PythonDir + "/Modules/" + f,
		[
			"main.c",
			"python.c",
			"getbuildinfo.c",
			"posixmodule.c",
			"arraymodule.c",
			"gcmodule.c",
			"_csv.c",
			"_collectionsmodule.c",
			"itertoolsmodule.c",
			"operator.c",
			"_math.c",
			"mathmodule.c",
			"errnomodule.c",
			"_weakref.c",
			"_sre.c",
			"_codecsmodule.c",
			"cStringIO.c",
			"timemodule.c",
			"datetimemodule.c",
			"shamodule.c",
			"sha256module.c",
			"sha512module.c",
			"md5.c",
			"md5module.c",
			"_json.c",
			"_struct.c",
			"_functoolsmodule.c",
			"threadmodule.c",
			"binascii.c",
			"_randommodule.c",
			"socketmodule.c",
			"_ssl.c",
			"zlibmodule.c",
			"selectmodule.c",
			"signalmodule.c",
			"fcntlmodule.c",
			"unicodedata.c",
			])) | \
	set(glob(PythonDir + "/Modules/_io/*.c"))

# remove main.c/python.c if we dont want an executable
if not buildExec:
	modFiles -= set([PythonDir + "/Modules/python.c"])

objFiels = \
	set(glob(PythonDir + "/Objects/*.c"))

parserFiles = \
	set(glob(PythonDir + "/Parser/*.c")) - \
	set(glob(PythonDir + "/Parser/*pgen*.c"))


compileOpts = CFLAGS + [
	"-Ipylib",
	"-I" + PythonDir + "/Include",
	# "-DWITH_PYCRYPTO",
]


def execCmd(cmd):
	cmdFlat = " ".join(cmd)
	print cmdFlat
	return os.system(cmdFlat)
	
def compilePyFile(f, compileOpts):
	ofile = os.path.splitext(os.path.basename(f))[0] + ".o"
	try:
		if os.stat(f).st_mtime < os.stat("build/" + ofile).st_mtime:
			return ofile
	except: pass
	cmd = [CC] + compileOpts + ["-c", f, "-o", "build/" + ofile]
	if execCmd(cmd) != 0:
		sys.exit(1)
	return ofile

def compilePycryptoFile(fn):
	return compilePyFile(fn, compilePycryptoOpts)
	
def compile():
	ofiles = []
	for f in list(baseFiles) + list(modFiles) + list(objFiels) + list(parserFiles):
		ofiles += [compilePyFile(f, compileOpts)]
	
	if buildExec:
		execCmd([CC] + LDFLAGS + map(lambda f: "build/" + f, ofiles) + ["-o", "python"])
	else:
		#execCmd([LD] + LDFLAGS + map(lambda f: "build/" + f, ofiles) +
		#	["-o", "libpython.a"])
		# execCmd(["ar", "rcs", "libpython.a"] + map(lambda f: "build/" + f, ofiles))
		execCmd(
			[LIBTOOL, "-static", "-syslibroot", SDKROOT,
			 #"-arch_only", "armv7",
			 "-o", "libpython.a"] +
			map(lambda f: "build/" + f, ofiles) +
			map(lambda f: ("%s/lib/" % STATIC_LIB) + f, [
				"libssl.a",
				"libcrypto.a",
				"libgcrypt.a",
				"libsasl2.a",
				"libz.a",
				]))
		
if __name__ == '__main__':
	compile()

