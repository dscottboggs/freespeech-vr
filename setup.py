from setuptools import setup
from setuptools.command.install import install
from distutils import log
import os, shutil, sys, textwrap
APPNAME = "FreeSpeech"
CHK_DIR_FAIL = 5
REFDIR                  = os.path.join("/", "usr", "share", APPNAME)
# create reference directory
CONFDIR                 = os.path.join("/", "etc", APPNAME)
LIB_EXEC_DIR            = os.path.join("/", "usr", "local", "bin")
POCKETSPHINX_FILES_DIR  = os.path.join(REFDIR, 'pocketsphinx-data', 'en-US')
CUSTOM_PSX_FILES_DIR    = os.path.join(CONFDIR, 'pocketsphinx-data', 'en-US')
PSX_PARENT_DIR          = os.path.join(REFDIR, 'pocketsphinx-data')
REF_FILES={
    #"cmdjson"   : os.path.join(REFDIR, 'default_commands.json'),
    "lang_ref"  : os.path.join(REFDIR, 'freespeech.ref.txt'),
    "dic"       : os.path.join(POCKETSPHINX_FILES_DIR, 'pronounciation-dictionary.dict'),
    "lang_model": os.path.join(POCKETSPHINX_FILES_DIR, 'language-model.lm.bin')
}
CONF_FILES={
    "lang_ref"  : os.path.join(CONFDIR, 'freespeech.ref.txt'),
    "lang_model": os.path.join(CONFDIR, 'freespeech.lm'),
    "dic"       : os.path.join(CONFDIR, 'freespeech.dic'),
}
def check_dir(directory, recursive=None):
    """ Checks for existence of a necessary directory. If 'recursive' is
        not none, it needs to be a folder to be recursively copied
    """
    if recursive is None:
        try:
            if not os.path.isdir(directory):
                os.makedirs(directory)
                print("Successfully created", directory)
            else:
                print("Successfully accessed", directory)
        except OSError as this_error:
            errno, strerror = this_error.args
            print(("in check_dir (" + str(directory) + ") --"),
                    (str(errno) + ":"), strerror)
    else:
        assert isinstance(recursive, str),\
            "Source directory in check_dir must be passed as a string."
        if os.path.isdir(directory):
            shutil.rmtree(directory)
        elif os.access(directory, os.F_OK):
            print("File", directory, "exists and is not a directory, but",
                recursive,
                "was attempted to be overwritten. This is strange.",
                "Not continuing")
            exit(CHK_DIR_FAIL)
        shutil.copytree(recursive, directory)

def check_file(filename, ref_file=None, permissions=None):
    """ Checks to see if a file exists. If there is a default
        configuration that can be assigned, pass it as the ref_file
    """
    try:
        if not os.access(filename, os.W_OK):
            if ref_file is None:
                raise OSError
            else:
                shutil.copy(ref_file, filename)
                print("Successfully created", filename)
        if permissions is not None:
            os.chmod(filename, permissions)
        print("Successfully accessed", filename)
    except OSError as this_error:
        errno, strerror = this_error.args
        print("In setup.py; check_file.",
            "File: " + filename,
            "Reference file: " + ref_file,
            "Error Number: " + str(errno),
            "Error Message: " + strerror,
            sep='\n\t')
# Create reference directory
check_dir(REFDIR, recursive=os.getcwd())

if not os.access("/usr/tmp",os.W_OK):
    os.symlink("/tmp","/usr/tmp")
check_dir(CONFDIR)
check_dir(REFDIR)
check_dir(PSX_PARENT_DIR)
check_file(os.path.join(REFDIR, 'language_ref.txt'),
    os.path.join(os.getcwd(),'language_ref.txt'))
check_file(CONF_FILES['lang_ref'],  REF_FILES['lang_ref'])
check_file(CONF_FILES['dic'],       REF_FILES['dic'])
check_file(CONF_FILES['lang_model'],REF_FILES['lang_model'])
check_dir(CUSTOM_PSX_FILES_DIR,     recursive=POCKETSPHINX_FILES_DIR)
#check_file(CONF_FILES['cmdjson'],  REF_FILES['cmdjson'])
cmu_cam_tk_files = [
    'binlm2arpa',
    'evallm',
    'idngram2lm',
    'idngram2stats',
    'interpolate',
    'mergeidngram',
    'ngram2mgram',
    'text2idngram',
    'text2wfreq',
    'text2wngram',
    'wfreq2vocab',
    'wngram2idngram'
]
for f in cmu_cam_tk_files:
    # checks to see if each executable file exists. If it doesn't, copies
    # it from REFDIR and makes executable if it isn't already
    check_file(os.path.join(LIB_EXEC_DIR, f),
        os.path.join(REFDIR, 'CMU-CamTK_bin', f))
    if not os.access(os.path.join(LIB_EXEC_DIR, f), os.X_OK):
        os.chmod(os.path.join(LIB_EXEC_DIR, f), 755)
setup(
    name=APPNAME,
    version='0.3.0a',
    author="Henry Kroll III",
    maintainer="D. Scott Boggs",
    maintainer_email="scott@tams.tech",
    url="https://thenerdshow.com/freespeech-vr",
    download_url="https://github.com/dscottboggs/freespeech-vr",
    description="Continuous engine-independent realtime speech recognition",
    long_description=str(textwrap.dedent("""
    FreeSpeech is a text editor with built-in engine-independent speech
    recognition powered by python's speech_recognition engine. It has a
    set of rudimentary commands for controlling events in the text entry
    area, learning new words and phrases, and plans to support training
    an acoustic model on the fly for pocketsphinx. I intend to write a
    command-and-control derivative called FreezePeach.
        Supported engines:
          - PocketSphinx
          - Google Voice
    This package includes binaries and source files for applications
    other than freespeech, which are not available currently in the
    Debian stable repository. Namely,
      - The CMU/Cambridge statistical modelling toolkit
      - a python send_keys library
      - Python3's speech_recognition library""")),
    license='GPLv3',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Gtk',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: GPLv3',
        'Operating System :: POSIX',
        'Programming Language :: Python',
    ]
)
