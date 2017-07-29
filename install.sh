#!/bin/bash
#	Install script for FreeSpeech
#
#	Checks for missing dependencies, and installs them if necessary. This
#		particular install script is for the Python3 version on Debian 9
#		Stretch, and should work with the current Ubuntu 16 LTS and 17
#		versions. If you have a different system and successfully (or 
#		unsuccessfully) installed FreeSpeech, please raise an issue
#		describing your system and how you installed or attempted to
#		install FreeSpeech on your system, including the exact commands 
#		you used so that we can add your system to the script.
#
#

python3_deps=(python3-xlib python-simplejson python3-gi python-pocketsphinx)
sphinx_deps=(python-sphinxbase sphinxbase-utils sphinx-common)
gstreamer1_deps=(python3-gst-1.0 gstreamer1.0-pocketsphinx gstreamer1.0-plugins-base gstreamer1.0-plugins-good ) 
python3_ALL_deps=(${python3_deps[@]} ${sphinx_deps[@]} ${gstreamer1_deps[@]})

# todo add Jessie and check Ubuntu flavors

echo "Creating necessary files and folders."
if [ -z "$(cat $HOME/.bashrc | grep 'XDG_CONFIG_HOME')" ]; then
	echo "export XDG_CONFIG_HOME=$HOME/.config" >> $HOME/.bashrc
fi
export XDG_CONFIG_HOME=$HOME/.config
if ! [ -d /usr/tmp/ ]; then
	sudo ln -s /tmp /usr/tmp
fi
if [ "$(lsb_release -cs)" = "stretch" ]; then
	release=stretch
elif [ "$(lsb_release -cs)" = "jessie" ]; then
	release=jessie
elif [ "$(lsb_release -cs)" = "xenial" ] || [ "$(lsb_release -cs)" = "yakkety" ] || [ "$(lsb_release -cs)" = "zesty" ] || [ "$(lsb_release -cs)" = "wily" ] || [ "$(lsb_release -cs)" = "trusty" ]; then
	release=ubuntu
fi
if [ "$(uname -m)" = "x86_64" ]; then
	ARCH=amd64
elif [ "$(uname -m)" = "i686" ]; then
	ARCH=i386
else 
	echo "Unknown architecture, please follow manual instructions or edit\
	the install script with the appropriate ARCH value - amd64 or\
	i386. If your system is not Intel based, you will need to locate\
	the source files and attempt to build them on your system.\
	Good luck."
	exit 1
fi
if [ "$release" != "stretch" ] && [ "$release" != "ubuntu" ] && [ "$release" != "jessie" ]; then
	echo "Unknown linux version, please refer to manual \
installation or update the script to reflect your\
system's requirements. Linux version reported:\
$release"
	exit 1
fi

echo "installing dependencies"

if [ "$release" = "stretch" ]; then
	sudo apt install ${python3_ALL_deps[@]}
fi
# todo python2 version setup on Jessie

mkdir -p $XDG_CONFIG_HOME/FreeSpeech/Downloads/
cd $XDG_CONFIG_HOME/FreeSpeech/Downloads/

git clone https://github.com/dscottboggs/freespeech-vr.git
if [ "$release" = "stretch" ]; then
	echo "setting up python3 version"
	cd freespeech-vr/
	git checkout python3
	cd ..
fi
if [ ! -f "freespeech-vr/endian.c" ]; then
	echo "error downloading git repo"
	exit 1
fi

gcc freespeech-vr/endian.c -o freespeech-vr/endian
echo "Downloading and building CMU-Cambridge Statistical Language Modeling Toolkit v2"
wget http://www.speech.cs.cmu.edu/SLM/CMU-Cam_Toolkit_v2.tar.gz
tar xzvf CMU-Cam_Toolkit_v2.tar.gz
cd $XDG_CONFIG_HOME/FreeSpeech/Downloads/CMU-Cam_Toolkit_v2/src
# endian outputs an exit code based on the endian-ness of your system
$XDG_CONFIG_HOME/FreeSpeech/Downloads/freespeech-vr/endian
case $? in
	1) echo "big endian install"
	;;
	2) echo "Little endian install"
	cp Makefile Makefile.bak
	pwd
	cat Makefile | sed 's|#BYTESWAP_FLAG|BYTESWAP_FLAG|' > Makefile.tmp
	mv Makefile.tmp Makefile
	;;
	*) echo "error in detecting endian-ness"
	exit 1
	;;
esac
# this ^^ is required for the CMU-Cambridge toolkit.
make
sudo cp ../bin/* /usr/local/bin/
cp $XDG_CONFIG_HOME/FreeSpeech/Downloads/freespeech-vr/freespeech.desktop /usr/share/applications/

echo "Installation should be complete. Please check the\
output of the script for errors, test pocketsphinx\
with pocketsphinx_continuous and set your audio\
device in QJackCtl. Then you will be able to run\
freespeech.py"
