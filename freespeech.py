#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# FreeSpeech
# Copyright (C) 2016 Henry Kroll III, http://www.TheNerdShow.com
# Continuous realtime speech recognition and control

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ATTN: This version requires Gstreamer-1.0 and python3-gobject
# Compile sphinxbase and pocketsphinx from source
# since Gstreamer-1.0 packages are probably not available yet.
# See https://sourceforge.net/p/cmusphinx/discussion/help/thread/6a286ad1/

import platform, os, shutil, sys, codecs, subprocess, time, re, json, textwrap
import gi
from send_key import *
gi.require_version('Gtk', '3.0')
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk # Gdk is not used, but was
# originally listed as imported. Perhaps it will be required at some point.
GObject.threads_init()
Gst.init(None)

""" global variables """
appname = 'FreeSpeech'
refdir = 'lm'
gtk = Gtk
SUCCESSFULLY, ERROR, SUBPROCESS_FAILURE = 0,1,2
LOW, NORMAL, HIGH, FATAL = 0,1,2,3
LOG, DEBUG, WARN = 0,3,4 # ERROR and SUBPROCESS_FAILURE were already set as exit codes.
loglvl = [ "LOG", "ERROR", "SUBPROCESS_MESSAGE", "DEBUG", "WARN" ]
python3_deps = "python3-xlib", "python-simplejson", "python3-gi", "python-pocketsphinx"
sphinx_deps    = "python-sphinxbase", "sphinxbase-utils"," sphinx-common"
gstreamer1_deps = "python3-gst-1.0", "gstreamer1.0-pocketsphinx", "gstreamer1.0-plugins-base", "gstreamer1.0-plugins-good"
dependencies = python3_deps + sphinx_deps + gstreamer1_deps
toolkit_dependencies = "text2wfreq", "wfreq2vocab", "text2wngram", "text2idngram", "ngram2mgram", "wngram2idngram", "idngram2stats", "mergeidngram", "idngram2lm", "binlm2arpa", "evallm","interpolate"
refdir  = os.path.join("/", "usr", "share", "freespeech")
confdir = os.path.join("/", "etc", "freespeech")
# note refdir will have to be redefined if the system is Windows, as Windows doesn't have an /etc
# perhaps the Windows dev could create an installer which creates a C:\Program Files\FreeSpeech\
# and put it in there.

# To be explicitly clear, reference files are files that are packaged
# with FreeSpeech and contain default values,
ref_files={
    "cmdjson"    : os.path.join(refdir, 'default_commands.json'),
    "lang_ref"   : os.path.join(refdir, 'freespeech.ref.txt'),
    "dic"        : os.path.join(refdir, 'custom.dic')
}
# configuration files are files that are *generated* by FreeSpeech and
# contain custom configurations.
conf_files={
    "lang_ref"  : os.path.join(confdir, 'freespeech.ref.txt'),
    "vocab"     : os.path.join(confdir, 'freespeech.vocab'),
    "idngram"   : os.path.join(confdir, 'freespeech.idngram'),
    "arpa"      : os.path.join(confdir, 'freespeech.arpa'),
    "dmp"       : os.path.join(confdir, 'freespeech.dmp'),
    "cmdtext"   : os.path.join(confdir, 'freespeech.cmd.txt'),
    "cmdjson"   : os.path.join(confdir, 'freespeech.cmd.json'),
    "dic"       : os.path.join(confdir, 'custom.dic')
}


class FreeSpeech(object):
    """GStreamer/PocketSphinx Continuous Speech Recognition"""
    def __init__(self):
        # Messenger is for showing dialogs

        self.err=Messenger(parent=None)
        """Initialize a freespeech object"""

        # initialize components
        self.prereqs()
        self.editing = False
        self.ttext = ""
        self.init_gui()
        self.err.set_parent(self)
        self.init_commands()
        self.init_file_chooser()
        self.init_gst()
    def prereqs(self):
        try:
            # place to store the currently open file name, if any
            self.open_filename=''
            # create confdir if not exists
            if not os.access(confdir, os.R_OK):
                os.mkdir(confdir)
            # copy lang_ref to confdir if not exists
            if not os.access(conf_files["lang_ref"], os.R_OK):
                shutil.copy(ref_files["lang_ref"], conf_files["lang_ref"])
            # copy dictionary to confdir if not exists
            if not os.access(conf_files["dic"], os.R_OK):
                shutil.copy('custom.dic', conf_files["dic"])
        except OSError as this_error:
            errno,strerror=this_error.args
            self.err.show(errormsg = "in __init__ -- " + str(errno) + ": " + strerror, severity = FATAL)
        # Check for /usr/tmp, a library requires it.
        if not os.access("/usr/tmp/",os.W_OK):
            try:
                subprocess.call("sudo ln -s /tmp /usr/tmp",shell=True,executable='/bin/bash')
                if os.access("/usr/tmp",os.W_OK):
                    print("successfully created /usr/tmp")
                else:
                    # I feel like I have a tendency to write code that will never be reached
                    # but I'd rather have it there in case something bizzarre happens
                    # so I can track it down.
                    print("Uncaught error creating /usr/tmp. Does it exist? Is it writable?")
                    exit(ERROR)
            except OSError:
                print("You do not have a /usr/tmp folder or it is not writable. Attempts to resolve this have failed.")
                exit(SUBPROCESS_FAILURE)
        # Check for jack
        ps_aux_grep_jack = subprocess.check_output("ps aux | grep jack",shell=True,executable='/bin/bash').decode()
        if "/bin/jackd " not in ps_aux_grep_jack:
            #print (ps_aux_grep_jack)
            self.err.set_title("JACK not running")
            self.err.set_buttons((gtk.STOCK_CANCEL, gtk.ResponseType.CANCEL,
                    gtk.STOCK_NO, gtk.ResponseType.NO,
                    gtk.STOCK_YES, gtk.ResponseType.YES))
            response = self.err.run(errormsg=textwrap.dedent('''\
                JACK Audio Connection Kit is not running.
                Would you like to start QJackCtl to set up the
                audio? You can also press "no" to continue,
                or cancel to cancel starting FreeSpeech.'''))
            if response == gtk.ResponseType.CANCEL:
                exit(SUCCESSFULLY)  # the exit is succesful rather than error because the user has elected to close
            elif response == gtk.ResponseType.NO:
                self.err.set_defaults()
                return()
            elif response == gtk.ResponseType.YES:
                """
                 If you simply call "qjackctl", python will execute
                 it then move on. We need to keep the main app from
                 loading until jackd has started, so we are going to
                 put it inside of a loop which checks to see if
                 jackd is running
                """
                counter=0
                try:
                    subprocess.call("qjackctl")
                except OSError:
                    self.err.set_title("QJackCtl is not installed!")
                    self.err.show(errormsg="Please install QJackCtl or start jackd with the proper values.")
                    exit(SUBPROCESS_FAILURE)
                while ("/usr/bin/jackd" not in str(subprocess.check_output( "ps aux | grep jack", shell=True, executable='/bin/bash' ))):
                    time.sleep(1)
                    if (counter < 20): # Wait 20 seconds for JACK to start
                        counter+=1
                    else: # then throw an error 
                        err=messenger.__init__(title="Couldn't start JACK")
                        self.err.show(severity=FATAL)
                self.err.set_defaults()
                return()
            else:
                print("init_prereqs(): Invalid response from audioPrompt: " + str(response))
                exit(ERROR)

    def log_msg(self, msg , msgtype=LOG):
        print("FreeSpeech: ", loglvl[msgtype], " -- ", msg)

    def init_gui(self):
        self.undo = [] # Say "Scratch that" or "Undo that"
        """Initialize the GUI components"""
        self.window = Gtk.Window()
        # Change to executable's dir
        if os.path.dirname(sys.argv[0]):
            os.chdir(os.path.dirname(sys.argv[0]))
        #self.icon = Gdk.pixbuf_new_from_file(appname+".png")
        self.window.connect("delete-event", Gtk.main_quit)
        self.window.set_default_size(200, 200)
        #self.window.set_border_width(10)
        #self.window.set_icon(self.icon)
        self.window.set_title(appname)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox(homogeneous=False)
        self.text = Gtk.TextView()
        self.accel = Gtk.AccelGroup()
        accel_key, accel_mods = Gtk.accelerator_parse("<Ctrl>z")
        self.accel.connect(accel_key, accel_mods, 0, self.doscratch)
        self.window.add_accel_group(self.accel)
        self.textbuf = self.text.get_buffer()
        self.textbuf.connect("insert-text", self.text_inserted)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.scroller = Gtk.ScrolledWindow(None, None)
        self.scroller.set_policy(Gtk.ScrollablePolicy.NATURAL, Gtk.ScrollablePolicy.NATURAL)
        self.scroller.add(self.text)
        vbox.pack_start(self.scroller, True, True, 5)
        vbox.pack_end(hbox, False, False, False)
        self.button0 = Gtk.Button("Learn")
        self.button0.connect('clicked', self.learn_new_words)
        self.button1 = Gtk.ToggleButton("Send keys")
        self.button1.connect('clicked', self.toggle_echo)
        self.button2 = Gtk.Button("Show commands")
        self.button2.connect('clicked', self.show_commands)
        self.button3 = Gtk.ToggleButton("Mute")
        self.button3.connect('clicked', self.mute)
        hbox.pack_start(self.button0, True, False, 0)
        hbox.pack_start(self.button1, True, False, 0)
        hbox.pack_start(self.button2, True, False, 0)
        hbox.pack_start(self.button3, True, False, 0)
        self.window.add(vbox)
        self.window.show_all()

    def init_file_chooser(self):
        self.file_chooser = Gtk.FileChooserDialog(title="File Chooser",
        parent=self.window, action=Gtk.FileChooserAction.OPEN,
        buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))

    def init_commands(self):
        self.commands = Commands()  # The object created by commands.py that acts upon the Commnds
        me = self.prefsdialog = gtk.Dialog("Command Preferences", None,
            0,  # In previous versions of Gtk this was Gtk.DIALOG_DESTROY_WITH_PARENT, but
            #in the current version of Gtk that is invalid. The first result on DuckDuckGo
            # suggtests passing 0 directly, so lets see what happens then...
            (gtk.STOCK_CANCEL, gtk.ResponseType.REJECT,
            gtk.STOCK_OK, gtk.ResponseType.ACCEPT))
        self.cmds = commands.load_commands() # cmds becomes the data structure of the literal commands
        cmd_text = []
        for command_name,command in self.cmds.iter():
            for phrase in command["training_phrases"]:
                cmd_text.append("<s> " + phrase + " </s>") 
#   apparently pocketsphinx parses phrases to add to the dictionary by reading
#   them from XML <s> tags. 
        try:
            with open(conf_files["cmdtext"], encoding='utf-8', mode='w') as txtfile:
                for text in cmd_text:
                    txtfile.write(text)
        except OSError as e:
            no,msg = e.args
            self.err.show(errormsg= no + ": " + msg + "\n...Occurred in init_commands()", severity=FATAL)

        me.label = gtk.Label( \
"Double-click to change command wording.\n\
If new commands don't work click the learn button to train them.")
        me.vbox.pack_start(me.label)
        me.checkbox=gtk.CheckButton("Restore Defaults")
        me.checkbox.show()
        me.action_area.pack_start(me.checkbox)
        me.liststore=gtk.ListStore(str, str)
        me.liststore.set_sort_column_id(0, gtk.SORT_ASCENDING)
        me.tree=gtk.TreeView(me.liststore)
        editable = gtk.CellRendererText()
        fixed = gtk.CellRendererText()
        editable.set_property('editable', True)
        editable.connect('edited', self.edited_cb)
        me.connect("expose-event", self.prefs_expose)
        me.connect("response", self.prefs_response)
        me.connect("delete_event", self.prefs_response)
        column = gtk.TreeViewColumn("Spoken command",editable,text=0)
        me.tree.append_column(column)
        column = gtk.TreeViewColumn("What it does",fixed,text=1)
        me.tree.append_column(column)
        me.vbox.pack_end(me.tree)
        me.label.show()
        me.tree.show()
        self.commands_old = self.cmds
        me.show_all()

    def prefs_expose(self, me, event):
        """ callback when prefs window is shown """
        # populate commands list with documentation
        me.liststore.clear()
        for command_name,command in self.cmds.iter():
            for phrase in command["training_phrases"]:
                me.liststore.append([command_name,phrase])
                print(command_name,phrase,sep="  --  ")

    def read_prefs(self):
        try:
            """ read command list from file """
            with codecs.open(conf_files["cmdjson"], encoding='utf-8', mode='r') as f:
                self.cmds=json.loads(f.read())
        except OSError as e:
            no,msg = e.args
            self.err.show(errormsg = no + ": " + msg + "\n...Occurred in read_prefs()", severity=FATAL)

    def prefs_response(self, me, event):
        """ make prefs dialog non-modal by using response event
            instead of run() method, which waited for input """
        if me.checkbox.get_active():
            # Copy current vocab to commands.json.bak if exists.
            if (os.access(conf_files["commands.json"],os.R_OK)):
                shutil.copy(conf_files["commands.json"],os.path.join(confdir,"commands.json.bak"))
            # Note that this only creates one level of backup. If you go to the preferences menu and
            # choose "restore defaults" twice, it will overwrite the backup with the defaults as well.
            shutil.copy(ref_files["commands.json"],conf_files["commands.json"])
        else:
            if event!=Gtk.ResponseType.OK:
                self.cmds = self.commands_old
            else:
                self.write_prefs()
                # big TODO
#   So we need to add all of the training phrases to their appropriate commands and rewrite both the 
#       commands.json and commans.txt files. See init_commands() for reference
        me.hide()
        return True

    def edited_cb(self, cellrenderertext, path, new_text):
        """ callback activated when treeview text edited """
        #~ self.prefsdialog.tree.path=new_text
        liststore=self.prefsdialog.liststore
        treeiter = liststore.get_iter(path)
        old_text = liststore.get_value(treeiter,0)
        if new_text not in self.cmds:
            liststore.set_value(treeiter,0,new_text)
            self.cmds[new_text]=self.cmds[old_text]
            del(self.cmds[old_text])
            #~ print(old_text, new_text)
        for command_name,command in self.cmds.iter():
            if cellrenderertext == command_name:
                command["training_phrases"].append(new_text)
    def show_commands(self, argument=None):
        """ show these command preferences """
        me=self.prefsdialog
        self.commands_old = self.commands
        me.show_all()
        me.present()
        return True # command completed successfully!

    # Oh man, what a beautifully simple method. final_result(hypothesis,confidence).
    # perhaps the sphinx utility offers a way to return a list of hypotheses sorted
    # by confidence for a simple "go back and fix that bit" method. We shall see,
    # once functionality is established.
    def element_message(self, bus, msg):
        """Receive element messages from the bus."""
        msgtype = msg.get_structure().get_name()
        if msgtype != 'pocketsphinx':
            return

        if msg.get_structure().get_value('final'):
            commands.search(heard_str = msg.get_structure().get_value('hypothesis'), confidence = msg.get_structure().get_value('confidence'))
            # self.pipeline.set_state(Gst.State.PAUSED)
            # self.button1.set_active(False)
        elif msg.get_structure().get_value('hypothesis'):
            self.partial_result(msg.get_structure().get_value('hypothesis'))

    def init_gst(self):
        """Initialize the speech components"""
        self.pipeline = Gst.parse_launch('autoaudiosrc ! ladspa-gate-1410-so-gate threshold=-23.0 decay=2.0 hold=2.0 attack=0.01 ! audioconvert ! audioresample ! pocketsphinx name=asr ! fakesink')
        # this line ^^^ handles bringing the audio in from jackd, processing it for minor noise reduction
        # and passing that to pocketsphinx. It requires Steve Harris' noise gate LADSPA plugin, which is 
        # a part of the swh-plugins package. We should possibly package that in the .deb archive, rather
        # than depending on the whole package, as we really only depend on one plugin. Alternatively, or
        # perhaps addtionally, we could utilize other plugins from that library to further process the
        # audio in order to get more reliable results from PocketSphinx (e.g.: adding a band-pass filter
        # for the typical range of human speech, rather than listening on the whole range of microphone
        # access).
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect('message::element', self.element_message)
        self.pipeline.set_state(Gst.State.PAUSED)

        asr = self.pipeline.get_by_name('asr')

        """Load custom dictionary and language model"""
        asr.set_property('dict', conf_files["dic"])

        # The language model that came with pocketsphinx works OK...
        # asr.set_property('lm', '/usr/share/pocketsphinx/model/lm/en_US/wsj0vp.5000.DMP')
        # but it does not contain editing commands, so we make our own
        if not os.access(conf_files["dmp"], os.W_OK): # create if not exists
            self.learn_new_words(None)
        elif os.path.getsize(conf_files["dmp"]) < 1:    # populate if empty
            self.learn_new_words(None)
        asr.set_property('lm', conf_files["dmp"])

        # Adapt pocketsphinx to your voice for better accuracy.
        # See http://cmusphinx.sourceforge.net/wiki/tutorialadapt_

        # asr.set_property('hmm', '../sphinx/hub4wsj_sc_8kadapt')

        #fixme: write an acoustic model trainer
        
        if not self.button3.get_active():
            self.pipeline.set_state(Gst.State.PLAYING)

    def learn_new_words(self, button):
        """ Learn new words, jargon, or other language
        
          1. Add the word(s) to the dictionary, if necessary.
          2. Type or paste sentences containing the word(s).
          2. Use the word(s) differently in at least 3 sentences.
          3. Click the "Learn" button. """
        
        # prepare a text corpus from the textbox
        corpus = self.prepare_corpus(self.textbuf)
        
        # append it to the language reference
        try:
            with codecs.open(conf_files["lang_ref"], encoding='utf-8', mode='a+') as f:
                for line in corpus:
                    if line:
                        f.write(line + '\n')
        except FileNotFoundError as e:
            num,msg=e.args
            self.err.show(errormsg= num + ": " + msg, severity= FATAL)
        except PermissionError as e:
            num,msg=e.args
            self.err.show(errormsg= num + ": " + msg,severity=FATAL)
        
        # cat command
        if platform.system()=='Windows':
            catcmd = 'type '
        else:
            catcmd = 'cat '
        
        # compile a vocabulary
        # http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html#text2wfreq
        print("Compiling vocabulary and saving to file.")
        try:
            subprocess.check_call(catcmd + (conf_files["cmdtext"] + ' ')*4 + conf_files["lang_ref"] + '|text2wfreq -verbosity 2 |wfreq2vocab -top 20000 -records 100000 > ' + conf_files["vocab"], shell=True)
        # this line adds the cmdtext list 4 times to increase likelyhood over lang_ref.
        # not sure if that's the best way to do things, but it seems to work.
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg= 'Trouble writing ' + conf_files["vocab"] + ": " + msg, severity=FATAL)
        # update the idngram\
        # http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html#text2idngram
        print("Updating idngram based on the new vocabulary")
        try:
            subprocess.check_call('text2idngram -vocab ' + conf_files["vocab"] + ' -n 3 < ' + conf_files["lang_ref"] + ' > ' + conf_files["idngram"], shell=True)
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg= 'Trouble writing ' + conf_files["idngram"] + ": " + msg, severity=FATAL)
        
        # (re)build arpa language model
        # http://drupal.cs.grinnell.edu/~stone/courses/computational-linguistics/ngram-lab.html
        print("Rebuilding arpa language model")
        try:
            subprocess.check_call('idngram2lm -idngram -n 3 -verbosity 2 ' + conf_files["idngram"] + \
            ' -vocab ' + conf_files["vocab"] + ' -arpa ' + conf_files["arpa"] + ' -vocab_type 1' \
            ' -good_turing', shell=True)
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg='Trouble writing ' + conf_files["arpa"] + ": " + msg)

        # convert to dmp
        if subprocess.call('sphinx_lm_convert -i ' + conf_files["arpa"] + \
            ' -o ' + conf_files["dmp"] + ' -ofmt dmp', shell=True):
            self.err.show(errormsg='Trouble writing ' + conf_files["dmp"])
        
        self.pipeline.set_state(Gst.State.NULL)
        self.init_gst()

##  Meta-commands    
    def file_open(self):
        """ open file dialog """
        response=self.file_chooser.run()
        if response==Gtk.ResponseType.OK:
            self.open_filename=self.file_chooser.get_filename()
            with codecs.open(self.open_filename, encoding='utf-8', mode='r') as f:
                self.textbuf.set_text(f.read())
        self.file_chooser.hide()
        self.window.set_title("FreeSpeech | "+ os.path.basename(self.open_filename))
        return True # command completed successfully!
    
    def file_save_as(self):
        """ save under a different name """
        self.open_filename=''
        return self.file_save()
    
    def file_save(self):
        """ save text buffer to disk """
        if not self.open_filename:
            response=self.file_chooser.run()
            if response==Gtk.ResponseType.OK:
                self.open_filename=self.file_chooser.get_filename()
            self.file_chooser.hide()
            self.window.set_title("FreeSpeech | "+ os.path.basename(self.open_filename))
        if self.open_filename:
            with codecs.open(self.open_filename, encoding='utf-8', mode='w') as f:
                f.write(self.textbuf.get_text(self.bounds[0],self.bounds[1]))
        return True # command completed successfully!
    
    def freespeech_help(self):
        """ show these command preferences """
        me=self.prefsdialog
        self.commands_old = self.cmds
        me.show_all()
        me.present()
        return True # command completed successfully!

    def mute(self, button):
        """Handle button presses."""
        if not button.get_active():
            button.set_label("Mute")
            self.pipeline.set_state(Gst.State.PLAYING)
        else:
            button.set_label("Speak")
            self.pipeline.set_state(Gst.State.PAUSED)
    
    def toggle_echo(self, button):
        """ echo keystrokes to the desktop """
        if not button.get_active():
            button.set_label("Send keys")
            button.set_active(False)
        else:
            button.set_label("Stop sending")
            button.set_active(True)

    def toggle_keys(self):
        """ echo keystrokes to the desktop """
        self.button1.set_active(True - self.button1.get_active())
        return True
    
    def time_up(self, textbuf):
        """ add changed textbuf to undo buffer """
        if self.editing:
            self.editing = False
            self.undo.append(self.ttext)
            self.ttext = ""
        return True
        
    def text_inserted(self, textbuf, itera, text, length):
        # start editing for 2 seconds
        if not self.editing:
            self.editing = True
            self.ttext = ""
            GObject.timeout_add_seconds(2, self.time_up, textbuf)
        self.ttext += text
        return True

    def collapse_punctuation(self, txt, starting):
        index = 0
        insert = self.textbuf.get_iter_at_mark(self.textbuf.get_insert())
        prior = self.textbuf.get_iter_at_offset(insert.get_offset() - 2)
        nxt = self.textbuf.get_iter_at_offset(insert.get_offset() + 1)
        nextchar = self.textbuf.get_text(insert, nxt, False) #next is a python keyword
        lastchars = self.textbuf.get_text(prior, insert, False)
        words = txt.split()
        # remove the extra text to the right of the punctuation mark
        while True:
            if (index >= len(words)):
                break
            word = words[index]
            if (re.match(r"^\W\w", word)):
                words[index] = word[0]
            index += 1
        txt = " ".join(words)
        txt = txt.replace(" ...ellipsis", " ...")
        # move space before punctuation to after
        txt = re.sub(r" ([^\w\s]+)\s*", r"\1 ", txt)
        # remove space after opening bracket, hyphen
        txt = re.sub(r"([({\[\-]) ", r"\1", txt).strip()
        # capitalize if necessary
        if (starting or re.match(".*[.?!:]",lastchars)) and len(txt) > 1:
            txt = txt[0].capitalize() + txt[1:]
        # add space to beginning if necessary
        if txt and re.match(r"[^.?!:,\-\"';^@]",txt[0]) and len(lastchars) and lastchars[-1] != " " and not starting:
            txt = " " + txt
        # add space to end if necessary
        # abort if text selected
        if not self.textbuf.get_selection_bounds():
            if len(nextchar) and (nextchar != " "):
                txt = txt + " "
        return txt
        
    def expand_punctuation(self, corpus):
        # tweak punctuation to match dictionary utterances
        for ind, line in enumerate(corpus):
            line = re.sub(r'--',          r'--dash',                  line)
            line = re.sub(r'- ',          r'-hyphen ',                line)
            line = re.sub(r'`',           r'`agrave',                 line)
            line = re.sub(r'=',           r'=equals-sign',            line)
            line = re.sub(r'>',           r'>greater-than-symbol',    line)
            line = re.sub(r'<',           r'<less-than-symbol',       line)
            line = re.sub(r'\|',          r'\|pipe-symbol',           line)
            line = re.sub(r'\. \. \.',    r'...ellipsis',             line)
            line = re.sub(r' \. ',        r' .dot ',                  line)
            line = re.sub(r'\.$',         r'.period',                 line)
            line = re.sub(r',',           r',comma',                  line)
            line = re.sub(r':',           r':colon',                  line)
            line = re.sub(r'\?',          r'?question-mark',          line)
            line = re.sub(r'"',           r'"quote',                  line)
            line = re.sub(r'([\w]) \' s', r"\1's",                    line)
            line = re.sub(r" '",          r" 'single-quote",          line)
            line = re.sub(r'\(',          r'(left-paren',             line)
            line = re.sub(r'\)',          r')right-paren',            line)
            line = re.sub(r'\[',          r'[left-bracket',           line)
            line = re.sub(r'\]',          r']right-bracket',          line)
            line = re.sub(r'{',           r'{left-brace',             line)
            line = re.sub(r'}',           r'}right-brace',            line)
            line = re.sub(r'!',           r'!exclamation-point',      line)
            line = re.sub(r';',           r';semi-colon',             line)
            line = re.sub(r'/',           r'/slash',                  line)
            line = re.sub(r'%',           r'%percent',                line)
            line = re.sub(r'#',           r'#sharp-sign',             line)
            line = re.sub(r'@',           r'@at-symbol',              line)
            line = re.sub(r'\*',          r'*asterisk',               line)
            line = re.sub(r'\^',          r'^circumflex',             line)
            line = re.sub(r'&',           r'&ampersand',              line)
            line = re.sub(r'\$',          r'$dollar-sign',            line)
            line = re.sub(r'\+',          r'+plus-symbol',            line)
            line = re.sub(r'§',           r'§section-sign',           line)
            line = re.sub(r'¶',           r'¶paragraph-sign',         line)
            line = re.sub(r'¼',           r'¼and-a-quarter',          line)
            line = re.sub(r'½',           r'½and-a-half',             line)
            line = re.sub(r'¾',           r'¾and-three-quarters',     line)
            line = re.sub(r'¿',           r'¿inverted-question-mark', line)
            line = re.sub(r'×',           r'×multiplication-sign',    line)
            line = re.sub(r'÷',           r'÷division-sign',          line)
            line = re.sub(r'° ',          r'°degree-sign ',           line)
            line = re.sub(r'©',           r'©copyright-sign',         line)
            line = re.sub(r'™',           r'™trademark-sign',         line)            
            line = re.sub(r'®',           r'®registered-sign',      line)
            line = re.sub(r'_',           r'_underscore',             line)
            line = re.sub(r'\\',          r'\backslash',              line)
            line = re.sub(r'^(.)',        r'<s> \1',                  line)
            line = re.sub(r'(.)$',        r'\1 </s>',                 line)
            corpus[ind] = line
        return corpus

    def prepare_corpus(self, txt):
        txt.begin_user_action()
        self.bounds = self.textbuf.get_bounds()
        text = txt.get_text(self.bounds[0], self.bounds[1], True)
        # break on end of sentence
        text = re.sub(r'(\w[.:;?!])\s+(\w)', r'\1\n\2', text)
        text = re.sub(r'\n+', r'\n', text)
        corpus= re.split(r'\n', text)       
        for ind, tex in enumerate(corpus):
            # try to remove blank lines
            tex = tex.strip()
            if not re.match(r".*\w.*", tex):
                try:
                    corpus.remove(ind)
                except:     # Except what?
                    pass
                continue
            # lower case maybe
            if len(tex) > 1 and tex[1] > 'Z':
                tex = tex[0].lower() + tex[1:]
            # separate punctuation marks into 'words'
            # by adding spaces between them
            tex = re.sub(r'\s*([^\w\s]|[_])\s*', r' \1 ', tex)
            # except apostrophe followed by lower-case letter
            tex = re.sub(r"(\w) ' ([a-z])", r"\1'\2", tex)
            tex = re.sub(r'\s+', ' ', tex)
            tex = tex.strip()
            # fix the ʼunicode charactersʼ
            tex = tex.encode('ascii', 'ignore').decode()
            corpus[ind] = tex
        return self.expand_punctuation(corpus)

    def partial_result(self, hyp):
        """Show partial result on tooltip."""
        self.text.set_tooltip_text(hyp)

    def final_result(self, hypothesis, confidence):
        """Insert the final result into the textbox."""
        # All this stuff appears as one single action
        self.textbuf.begin_user_action()
        self.text.set_tooltip_text(hypothesis)
        # get bounds of text buffer
        self.bounds = self.textbuf.get_bounds()
        # Fix punctuation
        hyp = self.collapse_punctuation(hyp, \
        self.bounds[1].starts_line())
        # handle commands
        for command_name,command in self.cmds.iter():
        # iterates through the entire list of commands
            if(command.fullmatch(re.compile(command["listen_for"]),hypothesis.strip().lower())):
            # if the "listen_for" field's regex matches with the hypothesis,
                commands.execute(cmd_type=command["cmd_type"],command=command["command"])
                # passes the value and type of command to commands.py
        ins = self.textbuf.get_insert()
        itera = self.textbuf.get_iter_at_mark(ins) # iter is a python keyword
        # @ Henry Kroll WTF does this do?
        self.text.scroll_to_iter(itera, 0, False, 0.5, 0.5)
        self.textbuf.end_user_action()

    """Process spoken commands"""
    def clear_edits(self):
        """ close file and start over without saving """
        self.textbuf.set_text('')
        self.open_filename=''
        self.window.set_title("FreeSpeech")
        self.undo = []
        return True # command completed successfully!
    def backspace(self):
        """ delete one character """
        start = self.textbuf.get_iter_at_mark(self.textbuf.get_insert())
        self.textbuf.backspace(start, False, True)
        return True # command completed successfully!
    def select(self,argument=None):
        """ select [text/all/to end] """
        if argument:
            if re.match("^to end", argument):
                start = self.textbuf.get_iter_at_mark(self.textbuf.get_insert())
                end = self.bounds[1]
                self.textbuf.select_range(start, end)
                return True # success
            search_back = self.searchback(self.bounds[1], argument)
            if re.match("^all", argument):
                self.textbuf.select_range(self.bounds[0], self.bounds[1])
                return True # success
            search_back = self.searchback(self.bounds[1], argument)
            if None == search_back:
                return True
            # also select the space before it
            search_back[0].backward_char()
            self.textbuf.select_range(search_back[0], search_back[1])
            return True # command completed successfully!
        return False
    def delete(self,argument=None):
        """ delete [text] or erase selection """
        if argument:
            # print("del "+argument)
            if re.match("^to end", argument):
                start = self.textbuf.get_iter_at_mark(self.textbuf.get_insert())
                end = self.bounds[1]
                self.textbuf.delete(start, end)
                return True # success
            search_back = self.searchback(self.bounds[1], argument)
            if None == search_back:
                return True
            # also select the space before it
            search_back[0].backward_char()
            self.textbuf.delete(search_back[0], search_back[1])
            return True # command completed successfully!
        self.textbuf.delete_selection(True, self.text.get_editable())
        return True # command completed successfully!
    def insert(self,argument=None):
        """ insert after [text] """      
        arg = re.match(r'\w+(.*)', argument).group(1)
        search_back = self.searchback(self.bounds[1], arg)
        if None == search_back:
            return True
        if re.match("^after", argument):
            self.textbuf.place_cursor(search_back[1])
        elif re.match("^before", argument):
            self.textbuf.place_cursor(search_back[0])
        return True # command completed successfully!
    def done_editing(self):
        """ place cursor at end """
        self.textbuf.place_cursor(self.bounds[1])
        return True # command completed successfully!
    def doscratch(self, a, b, c, d):
        self.scratch_that()
        return False
    def scratch_that(self,command=None):
        """ erase recent text """
        self.bounds = self.textbuf.get_bounds()
        if self.undo:
            scratch = self.undo.pop(-1)
            search_back = self.bounds[1].backward_search( \
                scratch, Gtk.TextSearchFlags.TEXT_ONLY)
            if search_back:
                self.textbuf.select_range(search_back[0], search_back[1])
                self.textbuf.delete_selection(True, self.text.get_editable())
                if self.button1.get_active():
                    b="".join(["\b" for x in range(0,len(scratch))])
                    send_string(b)
                    display.sync()
                return True # command completed successfully!
        return False
    def new_paragraph(self):
        """ start a new paragraph """
        self.textbuf.insert_at_cursor('\n')
        if self.button1.get_active():
            send_string("\n")
            display.sync()
        return True # command completed successfully!

    def searchback(self, itera, argument): # iter is a python keyword
        """helper function to search backwards in text buffer"""
        search_back = itera.backward_search(argument, Gtk.TextSearchFlags.TEXT_ONLY)
        if None == search_back:
            argument = argument.capitalize()
            search_back = itera.backward_search(argument, Gtk.TextSearchFlags.TEXT_ONLY)
        if None == search_back:
            argument = argument.strip()
            search_back = itera.backward_search(argument, Gtk.TextSearchFlags.TEXT_ONLY)
        return search_back

class Messenger(Gtk.Dialog):
    """
    Messenger objects hereafter are analogous to Gtk.Dialogs. All
    methods which act upon dialogs should be moved to this class, and
    called upon the object, rather than the methods being in the main
    FreeSpeech class.
    """
    title="Error"
    parent=None
    dialogFlags=Gtk.DialogFlags.MODAL
    buttons=0
    label = Gtk.Label("Nice label")
    def __init__(self, title="Error", parent=None, dialogFlags=Gtk.DialogFlags.MODAL, buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK)):
        freespeech = FreeSpeech()
        # Defaults are for error messages.
        self.set_title(title)
        self.set_parent(parent)
        self.set_flags(dialogFlags)
        self.set_buttons(buttons)
        # this ^^ for some reason includes the default value as well as things explicitly set
        #TODO ^^
        #FIXME ^^
        super().__init__(self.title, self.parent, self.dialogFlags, self.buttons)
        self.vbox.pack_start(self.label, False, False, False)
        self.label.show()

    def show(self, severity=NORMAL,parent=None,errormsg="no error message has been included"):
        if parent is None:
            parent=self
        if severity is LOW:
            freespeech.log_msg(msg=errormsg,msg_type=ERROR) 
        elif severity is FATAL:
            self.label.set_text(errormsg)
            self.run()
            self.hide()
            exit(ERROR)
        else:    # Normal severity
            self.label.set_text(errormsg)
            self.run()
            self.hide()
            set_defaults()
    def run(self, parent=None, errormsg="No error message has been included"):
        if parent is None:
            parent=self
        self.label.set_text(errormsg)
        return super().run()

    # getters and setters
    def set_defaults(self):
        set_title()
        set_flags()
        set_buttons()
    def set_title(self,title="Error"):
        self.title=title
    def set_buttons(self, buttons=(Gtk.STOCK_OK,Gtk.ResponseType.OK)):
        self.buttons=buttons
    def set_flags(self,flags=Gtk.DialogFlags.MODAL):
        self.dialogFlags=flags
    def set_parent(self, parent=None):
        self.parent=parent
    def get_title(self):
        return self.title
    def get_buttons(self):
        return self.buttons
    def get_flags(self):
        return self.dialogFlags
class Commands():
    """
    The Commands class defines the data structures and types of commands. 
    A the Commands object contains a dictionary of commands. These commands
    are defined in JSON in /etc/freespeech/commands.json, and can be of six
    types as of now: Python script, BASH script, REST API interaction,
    text-to-speech, sending of a series of keystrokes to the desktop, and
    meta-commands

    REST API interaction: Yet to be implemented. Performs a GET, POST, HEAD,
        etc. request and responds to the user in a defined way.
    TTS: Yet to be implemented. Speak a string. This will really only be
        useful if we can implement a conversational interface.
    Meta-Commands: For working with FreeSpeech and support for legacy text-
        editing commands, to be depricated in favor of more generic-style 
        commands that can be reinterpreted for various text editors (E.G. nano,
        vim, Eclipse, Sublime, or Collabora) by writing an extension module for
        that editor.
    """
    cmds            = {}
    quick_ref       = []
    confdir         = os.path.join("/", "etc", "freespeech")
    refdir          = os.path.join("/", "usr", "share", "freespeech")
    commands_json   = os.path.join(confdir,"commands.json")
    parent          = None
    training_phrases= []
    cmd_types       = ["PYTHON","BASH","REST","SAY","PRINT","META"]
    def __init__(self,parent=None):
        cmd_list = load_commands()
        self.parent=parent

    def new_command(self, name, listen_for, cmd_type, command, description, training_phrases):
        if name is None or listen_for is None or cmd_type is None or command is None or description is None or training_phrases.length() < 1 :
            freespeech.log_msg(msgtype=4, message="Incomplete command. Command not saved.")
        elif cmd_type not in cmd_types:
            freespeech.log_msg(msgtype=4,message="Command type " + cmd_type + " is not valid.")
        else:
            cmds=self.load_commands()
            cmds[name]={
                "listen_for":listen_for,
                "cmd_type": cmd_type,
                "command": command,
                "description": description,
                "training_phrases": training_phrases
            }
            with open(conf_files["cmdjson"], encoding='utf-8', mode='r') as cmd_file:
                cmd_file.write(json.dumps(cmds))
    def load_commands(self):
        try:
            with open(conf_files["cmdjson"], encoding='utf-8', mode='r') as cmd_file:
                if os.path.getsize(cmd_file) < 1:
                    shutil.copy(os.path.join(refdir,"default_commands.json"), os.path.join(confdir, "commands.json"))
                # copies a default set of commands to the configuration directory from the reference
                # directory if the one in the configuration dir is empty
                return json.loads(cmd_file)
        except OSError:
            try:
                shutil.copy(os.path.join(refdir,"default_commands.json"), os.path.join(confdir,"commands.json"))
                load_commands()
            except OSError:
                parent.err.show(errormsg="Cannot create commands.json in /etc/freespeech", severity=parent.FATAL)
    def create_quicker_reference(self):
        """
            This is SUPPOSED to speed things up a bit (considering 
            the task at hand this seems important, despite the inherent
            irony of trying to optimize in an interpreted language) by
            creating a list of tuples that uses the regex as a key for the
            name. I might nuke this later and just iterate through the
            list of commands. It seems at the moment (while working out
            the algorithm) this will be faster but I'm open to replacing
            it with something that better optimizes the task.
        """
        for cmd_name,cmd in cmd_list:
            self.quick_ref.append((cmd["listen_for"], cmd["Name"]))
    def search(self,heard_str,confidence):
        valid = False
        for c,d in quick_ref:
            if c.matches(heard_str):
                valid=True
                find_cmd(d)
        # valid should have been changed to True if a valid command was found 
        if valid==False:
            command_not_found()

    def find_cmd(self, name):
        for cmd in cmd_list:
            if name==cmd["Name"]:
                execute(cmd_type=cmd["cmd_type"],command=cmd["command"])

    def execute(self,cmd_type, command):
        if cmd_type is "PYTHON":
            exec(command)
        #elif cmd_type is "PYTHON2":
        #   idk how to do this. TODO, or fuck it?
        elif cmd_type is "BASH":
            unsuccessful = subprocess.check_call(command,shell=True)
            if unsuccessful > 0:
                self
        elif cmd_type is "REST":
            pass
        elif cmd_type is "SAY":
            pass
        elif cmd_type is "PRINT":
            send_string(command)
        elif cmd_type is "META":
            metacommmand(command)
        else:
            command_type_not_found
    def command_not_found():
        pass
    def command_type_not_found():
        pass

    def metacommand(command):
        eval("freespeech." + command + "()")
if __name__ == "__main__":
    app = FreeSpeech()
    Gtk.main()
