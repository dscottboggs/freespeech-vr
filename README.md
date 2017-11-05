# FreeSpeech-vr

*Experimental version for Python3, Gtk3, and Python's speech_recognition*

FreeSpeech is a free and open-source (FOSS), Python front-end for Carnegie Mellon University's excellent open source CMU Sphinx speech recognition toolkit, as well as several cloud-based speech-recognition engines.

In addition to dictation, FreeSpeech provides an interface dynamic language learning with pocketsphinx, voice commands, and keyboard emulation, so users can dictate into other apps, remote terminals, and virtual machines.

Get FreeSpeech via git from [Github](https://github.com/dscottboggs/freespeech-vr).

## Installation

# Windows: Most likely not. The application was written to be easily adapted to cross-platform capabilities, and is easily readable, but I am not familiar enough with the Windows filesystem nor the Windows installation process to be able to write in such capabilities. Specifically, the CMU/Cam statistical modelling toolkit requires access to a '/usr/tmp' and since windows has no '/' it cannot access said folder. If a windows developer could provide a pull request to resolve this issue it would be greatly appreciated. Otherwise, my only recommendations are Linux, virtual machines, or containers.

# Linux/Cygwin
The following packages should be installed through the package manager.

* [Python3](https://www.python.org/)
* [python3-gobject](https://wiki.gnome.org/Projects/PyGObject)
* [python-xlib](https://python-xlib.sourceforge.net/)
* [python-simplejson](https://undefined.org/python/#simplejson)
* [pocketsphinx, sphinxbase, and sphinxtrain](http://cmusphinx.sourceforge.net/) -- possibly available through your package manager. Check to be sure you can get version 5pre-alpha
* [speech_recognition python library](https://github.com/Uberi/speech_recognition/) -- not available on Debian, possibly others. Download from git and place in proper location
* [CMU-Cambridge Statistical Language Modeling Toolkit v2](http://www.speech.cs.cmu.edu/SLM/CMU-Cam_Toolkit_v2.tar.gz) ([documentation](http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html))

Distro packages may not exist yet. Compile sphinxbase and pocketsphinx from source. Use ./configure --prefix=/usr/local --libdir=/usr/local/lib64 and set environment variable for gstreamer1:

```bash
export GST_PLUGIN_SYSTEM_PATH_1_0=/usr/local/lib64/gstreamer-1.0:/usr/lib64/gstreamer-1.0
```

## Fedora packages, if available

```bash
su -c 'yum groupinstall "C Development Tools and Libraries"'
su -c 'yum -y install python3-gstreamer1 sphinxbase-libs \
pocketsphinx-libs pocketsphinx sphinxbase python3-pocketsphinx-plugin \
python-simplejson python-xlib python3-gobject git'
```

## Ubuntu packages, if available

```bash
sudo apt-get update

sudo apt-get python-xlib python-simplejson python-gtk3 python-gst1.0 \
gstreamer1.0-pocketsphinx sphinx-common python3-sphinxbase \
python3-pocketsphinx sphinxbase-utils git
```

If installation balks and says it can't find /media/cdrom the location may be different. The trick is to use the mount command from a terminal to discover where the cd is mounted and make it a link to /media/cdrom

```bash
sudo ln -s (location, change this) /media/cdrom
```

## Testing

Before we begin, load pavucontrol, Audacity (or some other audio recording program that has a recording monitor) and check sound levels.
Users should be able to record and play back audio at good volume, but not so high that it starts clipping.

```bash
arecord temp.wav -r 16000
aplay temp.wav
```

Test pocketsphinx

```bash
pocketsphinx_continuous
```

Say something. (It should print lots of spam while doing some (very basic) speech recognition). Don't stop until it recognizes some speech. Our software depends on a working pocketsphinx installation.

Download [CMU-Cam_Toolkit_v2](http://www.speech.cs.cmu.edu/SLM/CMU-Cam_Toolkit_v2.tar.gz) and unpack it. Read the instructions in the README and edit the Makefile. To summarize, most PC hardware is what they call "little-endian" and it requires this change: Edit `CMU-Cam_Toolkit_v2/src/Makefile` and remove the # sign in front of this line:

```bash
BYTESWAP_FLAG   = -DSLM_SWAP_BYTES
```


Run `make` to build the tools.

```bash
cd CMU-Cam_Toolkit_v2/src
make
```

Manually copy the tools from ../bin to somewhere in $PATH like: `/usr/local/bin`

```bash
sudo cp ../bin/* /usr/local/bin/
```

The tools expect to write to /usr/tmp

```bash
sudo ln -s /tmp /usr/tmp
```

Language files and preferences are copied to /home/$USER/.config but the location may be changed by changing or adding the environment variable, `$XDG_CONFIG_HOME`

```bash
export XDG_CONFIG_HOME=$HOME/.config
```

Get FreeSpeech using git.

```bash
cd ~/Downloads
git clone https://github.com/themanyone/freespeech-vr.git
```

## Using FreeSpeech

There is no desktop icon yet. Right-click on the desktop to create one.
Launching the program may be done via the Python interpreter.

```bash
cd ~/Downloads/frees*
python freespeech.py
```

Position the microphone somewhere near enough and begin talking. To end of the sentence, say "period" (or "colon", "question-mark", "exclamation-point") Look at the dictionary, "custom.dic" for ideas.

Voice commands are included. A list of commands pops up at start-up or say "show commands" to show them again. The following voice commands are supported (except only "scratch that" is available when using X keyboard emulation).

* file quit - quits the program
* file open - open a text file in the editor
* file save (as) - save the file
* show commands - pops up a customize-able list of spoken commands
* editor clear - clears all text in the editor and starts over
* delete - delete `[text]` or erase selected text
* insert - move cursor after word or punctuation example: "Insert after period"
* select - select `[text]` example: "select the states"
* go to the end - put cursor at end of document
* scratch that - erase last spoken text
* back space - erase one character
* new paragraph - equivalent to pressing Enter twice

## Troubleshooting

Prior to blaming freespeech, make sure audio recording and pocksphinx works. Run `pocketsphinx_continuous` from the command line in a terminal window to test it. If it has problems, check your pocketsphinx installation. We regret that we are not affiliated with CMU Sphinx and do not have the resources to support it.

In case of messages like this:

```bash
Trouble writing /home/*/.config/FreeSpeech/freespeech.idngram
Trouble writing...
```

It usually means nobody installed [CMU-Cambridge Statistical Language Modeling Toolkit v2](http://www.speech.cs.cmu.edu/SLM/CMU-Cam_Toolkit_v2.tar.gz) or there is a problem with the tools themselves. Edit the Makefile and follow the instructions therein before running `make`. Manually copy the files in the bin directory somewhere in your `$PATH` like `/usr/local/bin` on Linux or `C:\windows\system32` on Windows.

For some reason, the toolkit expects to be able to write to /usr/tmp. The `tmpfile()` function uses the P_tmpdir defined in `<stdio.h>`, but the Makefile installs everything under `/usr`. The quick-fix is to provide /usr/tmp for machines that don't have it.

```bash
sudo ln -s /tmp /usr/tmp
```

## Improving accuracy

The biggest improvements in accuracy have been achieved by adjusting the microphone position. Open up the volume control app. On systems that use pulseaudio (Fedora) volume level and microphone selection may be found using pavucontrol. Try making a recording with [Audacity](http://audacity.sourceforge.net) and checking the noise levels to make sure it sounds like intelligible speech when played back. Make sure freespeech is using the same mic levels in the volume controls recording tab.

Adapt PocketSphinx to a particular voice or accent for better accuracy.
See http://cmusphinx.sourceforge.net/wiki/tutorialadapt

## Language corpus

The language corpus that ships with this download, "freespeech.ref.txt" is likely to be very limited. Our excuse is that the small size saves memory while providing room to learn spoken grammar. Don't be surprised if it does not work very well at first. Use the keyboard to manually edit the text in the box until it says what was intended to say. Then hit the "Learn" button. It will try to do better at understanding next time! One may also train personalized grammar by pasting in gobs of text from previously authored websites and documents.

It seems that the PocketSphinx folks were trying to add support for capitalized words. If there is a word like "new" in the dictionary which could also be capitalized, as in "New Mexico" it is enough to make a capitalized copy like so:

```
*new  N UW
*New  N UW
```

Now train the new grammar, by using the capatalized form in a few sentences and pressing the Learn button. PocketSphinx will henceforth decide the capitalization depending on the context in which it appears. We tested it and it works! It capitalizes words like "New Mexico" and "The United States of America" but does not capitalize "altered states" nor "new pants". This is a wild idea, but maybe we could make a dictionary containing both capitalized and un-capitalized words. That would save us the effort of going through and capitalizing all the proper names. The only question is would the resulting dictionary be too big? The solution is probably to propose a patch to make PocketSphinx ignore case in the dictionary, using capitalization as it is found in the corpus, not the dictionary.

Don't worry if PocketSphinx learns bad grammar. It's not strictly necessary, but our corpus file, "lm/freespeech.ref.txt" may be manually corrected if it develops poor speech habits. Changes will apply next time anybody presses the "Learn" button.

The language model may be further [tweaked and improved](http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html#evallm).

## Dictionary

If there is a word that it stubbornly refuses to recognize, even after teaching it with several sentences, edit the dictionary: "freespeech.dic"

Sometimes the dictionary pronunciation can be little bit off. Notice that some other words have alternate pronunciations denoted with (2). Go ahead and change the pronunciation or add an alternate and see if it doesn't improve immediately the next time the program starts.

This dictionary is based on Pocketsphinx's cmu07a.dic because it contains punctuation, such as ".full-stop" and "?question-mark"). See "freespeech.dic" for the list of punctuation and their pronunciations. Adding new words to the dictionary may be done manually, along with their phonetic representation, but we are working on incorporating a word trainer.

About the CMU Pronouncing Dictionary
http://www.speech.cs.cmu.edu/cgi-bin/cmudict

## Security and privacy

FreeSpeech does not send any information over the network. Speech recognition is done locally using pocketsphinx. Learned speech patterns are stored in "plain text" format in "$HOME/.config/FreeSpeech/freespeech.ref.txt". Although the file should not be accessible to other users, it is nevertheless good practice not to teach FreeSpeech sensitive or private information like passwords, especially if others share access to the PC.
