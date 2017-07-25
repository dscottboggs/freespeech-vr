#!/bin/bash
echo "Creating necessary files and folders."
if [ -z "$(grep $HOME/.bashrc 'XDG_CONFIG_HOME')" ]; then
	echo "export XDG_CONFIG_HOME=$HOME/.config" >> $HOME/.bashrc
fi
export XDG_CONFIG_HOME=$HOME/.config
sudo ln -s /tmp /usr/tmp
mkdir -p $XDG_CONFIG_HOME/FreeSpeech/Downloads/
cd $XDG_CONFIG_HOME/FreeSpeech/Downloads/

echo "Downloading pocketsphinx and dependencies."
mkdir pocketsphinx
cd pocketsphinx
if [ $(uname -m) = "x86_64" ]; then
	ARCH=amd64
else if [ $(uname -m) = "i686" ]; then
	ARCH=i386
else
	echo ("Unknown architecture, please follow manual instructions or edit\
	the install script with the appropriate ARCH value - amd64 or\
	i386. If your system is not Intel based, you will need to locate\
	the source files and attempt to build them on your system.\
	Good luck.")
	exit 1
fi
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/gstreamer0.10-pocketsphinx_0.6-0svn6_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/libpocketsphinx-dev_0.6-0svn6_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/libpocketsphinx1_0.6-0svn6_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-hmm-en-hub4wsj_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-hmm-en-tidigits_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-hmm-zh-tdt_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-lm-en-hub4_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-lm-zh-hans-gigatdt_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-lm-zh-hant-gigatdt_0.6-0svn6_all.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/pocketsphinx-utils_0.6-0svn6_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/python-pocketsphinx-dbg_0.6-0svn6_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/python-pocketsphinx_0.6-0svn6_$ARCH.deb

echo "Downloading sphinxbase and dependencies."
mkdir ../sphinxbase
cd ../sphinxbase
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/libsphinxbase-dev_0.6-0svn5_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/libsphinxbase1_0.6-0svn5_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/python-sphinxbase-dbg_0.6-0svn5_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/python-sphinxbase_0.6-0svn5_$ARCH.deb
wget https://launchpad.net/~dhuggins/+archive/ubuntu/cmusphinx/+files/sphinxbase-utils_0.6-0svn5_$ARCH.deb

cd ..
echo "Installing the downloaded packages, fixing any related \
issues, and installing the remainder of the \
dependencies."
sudo apt update
sudo dpkg -i pocketsphinx/*.deb sphinxbase/*.deb
sudo apt install -f python-xlib python-simplejson python-gtk2 python-gst0.1 git gstreamer-plugins-base gstreamer-plugins-good jackd libjack0 libjack-dev

echo "Cleaning up the installation files"
rm -r pocketsphinx sphinxbase
echo '"git"-ing the FreeSpeech files'
git clone https://github.com/dscottboggs/freespeech-vr.git

if [ ! -f "freespeech-vr/endian.c" ]; then; echo "error downloading git repo"; exit 1; fi
echo "Downloading and building CMU-Cambridge Statistical Language Modeling Toolkit v2"
wget http://www.speech.cs.cmu.edu/SLM/CMU-Cam_Toolkit_v2.tar.gz
tar xzvf CMU-Cam_Toolkit_v2.tar.gz
gcc freespeech-vr/endian.c -o freespeech-vr/endian
freespeech-vr/endian
if [ $? -eq 1 ]; then
	echo "Big-endian installation"
else if [ $? -eq 2 ]; then
	echo "Little-endian installation"
	cat CMU-Cam_Toolkit_v2/src/Makefile | \
		sed 's|#BYTESWAP_FLAG|BYTESWAP_FLAG|' > \ 
		CMU-Cam_Toolkit_v2/src/Makefile
else
	echo "error checking endian-ness."
	exit $?
cd CMU-Cam_Toolkit_v2/src
make
cp ../bin/* /usr/bin/local/
echo "Installation should be complete. Please check the\
output of the script for errors, test pocketsphinx\
with pocketsphinx_continuous and set your audio\
device in QJackCtl. Then you will be able to run\
freespeech.py"
