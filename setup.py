from setuptools import setup
from setuptools.command.install import install
from distutils import log
import os, shutil, sys, textwrap
APPNAME = "FreeSpeech"

def check_dir(directory):
    """ Checks for existence of a necessary directory. """
    try:
        if not os.path.isdir(directory):
            os.makedirs(directory)
            print("Successfully created "+ directory)
        else:
            print("Successfully accessed "+ directory)
    except OSError as this_error:
        errno, strerror = this_error.args
        print(errormsg="in check_dir (" + str(directory)
            + ") -- "
            + str(errno)
            + ": "
            + strerror)
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
                print("Successfully created " + filename)
        if permissions is not None:
            os.chmod(filename, permissions)
        print("Successfully accessed " + filename)
    except OSError as this_error:
        errno, strerror = this_error.args
        print("In FreezePeach; check_file.\nFile: "
            + filename + "\nReference file: " + ref_file
            + "\nError Number: " + str(errno) + "\nError Message: "
            + strerror)

if not os.access("/usr/tmp",os.W_OK):
    os.symlink("/tmp","/usr/tmp")
confdir = os.path.join('etc', APPNAME)
refdir  = os.path.join('usr', 'share', APPNAME)
check_dir(confdir)
check_dir(refdir)
check_file(os.path.join(refdir, 'language_ref.txt'),
    os.path.join(os.getcwd(),'language_ref.txt'))
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
    check_file(os.path.join(refdir, f),
        os.path.join(os.getcwd(), 'CMU-CamTK_bin', f))
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
    an acoustic model on the fly for pocketsphinx.
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
