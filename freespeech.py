#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

     FreeSpeech
     Copyright (C) 2016 Henry Kroll III, http://www.TheNerdShow.com
               and 2017 D. Scott Boggs, Jr. https://madscientists.co
     Continuous engine-independent realtime speech recognition

     This program is free software: you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation, either version 3 of the License, or
     (at your option) any later version.

     This program is distributed in the hope that it will be useful,
     but WITHOUT ANY WARRANTY; without even the implied warranty of
     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
     GNU General Public License for more details.

     You should have received a copy of the GNU General Public License
     along with this program.  If not, see <http://www.gnu.org/licenses/>.

This application depends on the following libraries/applications being installed:
    Python libraries:
        python3-xlib python-simplejson python3-gi python-pocketsphinx send-key

  Cambrige/CMU statistical modelling toolkit binaries (architecture dependent, compile
    from source if a .deb package is not available for your system.):
        text2wfreq wfreq2vocab text2wngram text2idngram ngram2mgram wngram2idngram
        idngram2stats mergeidngram idngram2lm binlm2arpa evallm interpolate

Fully installed file structure on a POSIX based system (base your packages upon
this)
        File                        Location                                        Permissions
    freespeech binary:          /usr/local/bin/freespeech                               755
    send-key library bin:       /usr/local/bin/send-key                                 755
    CMU/Cam SLM kit:            /usr/local/bin/{the binaries}                           755
    Default commands file:      /usr/local/share/freespeech/default-commands.json       644
    Speech Recognition library: /usr/local/bin/speech_recognition                       755
    Default training files:     /usr/local/share/freespeech/pocketsphinx-data/en-US/*   655

"""

import json, os, platform, re, shutil, speech_recognition
import subprocess, sys, textwrap, time
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk # Gdk is not used, but was
# originally listed as imported. Perhaps it will be required at
# some point.
from send_key import *
GObject.threads_init()
# removing gstreamer dependency

""" global variables """
APPNAME                 = 'FreeSpeech'
SHORT_DESC              = 'Continuous engine-independent realtime speech recognition'
ENGINE                  = 'pocketsphinx'
SUCCESSFULLY, ERROR, SUBPROCESS_FAILURE = 0, 1, 2
LOW, NORMAL, HIGH, FATAL= 0, 1, 2, 3
LOG, DEBUG, WARN        = 0, 3, 4 # ERROR and SUBPROCESS_FAILURE were already set as exit codes.
loglvl                  = [ "LOG", "ERROR", "SUBPROCESS_MESSAGE", "DEBUG", "WARN" ]
refdir                  = os.path.join("/", "usr", "share", "freespeech")
confdir                 = os.path.join("/", "etc", "freespeech")
pocketsphinx_files_dir  = os.path.join(refdir, 'pocketsphinx-data', 'en-US')
# note refdir will have to be redefined if the system is Windows, as Windows doesn't have an /etc
# perhaps the Windows dev could create an installer which creates a C:\Program Files\FreeSpeech\
# and put it in there.

# To be explicitly clear, reference files are files that are packaged
# with FreeSpeech and contain default values,
ref_files={
    #"cmdjson"   : os.path.join(refdir, 'default_commands.json'),
    "lang_ref"  : os.path.join(refdir, 'freespeech.ref.txt'),
    "dic"       : os.path.join(pocketsphinx_files_dir, 'pronounciation-dictionary.dict'),
    "lm"        : os.path.join(pocketsphinx_files_dir, 'language-model.lm.bin')
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

def _undent_(text):
    """ shortcut for str(textwrap.dedent())"""
    assert isinstance(text, str), "Text to be un-indented must be a string! Received: " + str(text)
    return str(textwrap.dedent(text))

class FreeSpeech(object):
    """PyGTK continuous speech recognition scratchpad"""
    snore = None
    def __init__(self):
        # Messenger is for showing dialogs, logger is for logging
        self.logger = LogRecorder()
        self.err = Messenger(parent=None)
        """Initialize a freespeech object"""

        # initialize components
        self.prereqs()
        self.mike = speech_recognition.Microphone()
        self.wreck = speech_recognition.Recognizer()
        self.editing = False
        self.ttext = ""
        self.init_gui()
        self.err.set_parent(self)
        self.init_prefs()
        self.init_file_chooser()
        self.start_listening()
        #self.interface = Interface()
    def prereqs(self):
        # place to store the currently open file name, if any
        self.check_args()
        self.open_filename=''
        self.check_dir(confdir)
        self.check_file(conf_files['lang_ref'], ref_files['lang_ref'])
        self.check_file(conf_files['dic'],      ref_files['dic'])
        self.check_file(conf_files['arpa'],     ref_files['lm'])
        #self.check_file(conf_files['cmdjson'],  ref_files['cmdjson'])
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
                    self.logger.log_message(
                        "Uncaught error creating /usr/tmp. Does it exist? Is it writable?", ERROR)
                    exit(ERROR)
            except OSError:
                self.logger.log_message(_undent_("\
                    You do not have a /usr/tmp folder or it is not writable. Attempts to resolve\
                    this have failed.", ERROR))
                exit(SUBPROCESS_FAILURE)
        # Removed jack dependency.
    def check_dir(self, directory):
        """ Checks for existence of a necessary directory. """
        try:
            if not os.path.isdir(directory):
                os.makedirs(directory)
                self.logger.log_message("Successfully created "+ directory)
            else:
                self.logger.log_message("Successfully accessed "+ directory, DEBUG)
        except OSError as this_error:
            errno, strerror = this_error.args
            self.err.show_msg(errormsg="in check_dir (" + str(directory) + ") -- "
                + str(errno)
                + ": "
                + strerror, severity=FATAL)
    def check_file(self, filename, ref_file=None):
        """ Checks to see if a file exists. If there is a default configuration that can be
            assigned, pass it as the ref_file
        """
        try:
            if not os.access(filename, os.R_OK):
                if ref_file is None:
                    raise OSError
                else:
                    shutil.copy(ref_file, filename)
                    self.logger.log_message("Successfully created " + filename, DEBUG)
            self.logger.log_message("Successfully accessed " + filename, DEBUG)
        except OSError as this_error:
            errno, strerror = this_error.args
            self.err.show_msg(errormsg="In FreezePeach; check_file.\nFile: " + filename
                + "\nReference file: " + ref_file + "\nError Number: " + str(errno)
                + "\nError Message: " + strerror, severity=FATAL)
    def check_args(self):
        if APPNAME not in sys.argv:
            self.logger.log_message("The appliction was started under a name other than " + APPNAME
                + " this isn't a big deal but it is strange.")
        for i, arg in zip(range(len(sys.argv)), sys.argv):
            if arg is ("--help" or "-h"):
                self.display_help()
            if arg is ("-e" or "--engine"):
                ENGINE_ = sys.argv[i+1]
    def display_help(self):
        """ diplays a basic list of command line options. In this case we can assume this
            was run from the CLI and just use print, rather than the more generic Logger()
            which is there to allow easy conversion to logfiles rather than stdout logging
        """
        print(_undent_("""
            FreeSpeech -- continuous engine-independent speech recognition text editor

            FreeSpeech is a GUI application that can be launched without a command line
            for basic offline functionality. However, if you wish to use custom options
            (like a custom recognition engine), you can run it from the command line with
            the following flags:
                -h      --help          Shows this help text
                -e [?]  --engine [?]    Used to select a recognition engine. Available
                    options:
                        pocketsphinx    CMU sphinx
                        gv              Google voice
                        more options TODO"""))
    def init_gui(self):
        self.undo = [] # Say "Scratch that" or "Undo that"
        """Initialize the GUI components"""
        self.window = Gtk.Window()
        # Change to executable's dir
        if os.path.dirname(sys.argv[0]):
            os.chdir(os.path.dirname(sys.argv[0]))
        #self.icon = Gdk.pixbuf_new_from_file(APPNAME+".png")
        self.window.connect("delete-event", Gtk.main_quit)
        self.window.set_default_size(200, 200)
        #self.window.set_border_width(10)
        #self.window.set_icon(self.icon)
        self.window.set_title(APPNAME)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox(homogeneous=False)
        self.text = Gtk.TextView()
        self.undo_accel = Gtk.AccelGroup()
        accel_key, accel_mods = Gtk.accelerator_parse("<Ctrl>z")
        self.undo_accel.connect(accel_key, accel_mods, 0, self.doscratch)
        self.window.add_accel_group(self.undo_accel)
        self.textbuf = self.text.get_buffer()
        self.textbuf.connect("insert-text", self.text_inserted)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.scroller = Gtk.ScrolledWindow(None, None)
        self.scroller.set_policy(Gtk.ScrollablePolicy.NATURAL, Gtk.ScrollablePolicy.NATURAL)
        self.scroller.add(self.text)
        vbox.pack_start(self.scroller, True, True, 5)
        vbox.pack_end(hbox, False, False, False)
        self.learn_button = Gtk.Button("Learn")
        self.learn_button.connect('clicked', self.learn_new_words)
        self.echo_keys_button = Gtk.ToggleButton("Send keys")
        self.echo_keys_button.connect('clicked', self.toggle_echo)
        #self.prefs_dialog_button = Gtk.Button("Show commands")
        #self.prefs_dialog_button.connect('clicked', self.show_commands)
        self.kill_mike_button = Gtk.ToggleButton("Mute")
        self.kill_mike_button.connect('clicked', self.mute)
        hbox.pack_start(self.learn_button, True, False, 0)
        hbox.pack_start(self.echo_keys_button, True, False, 0)
        #hbox.pack_start(self.prefs_dialog_button, True, False, 0)
        hbox.pack_start(self.kill_mike_button, True, False, 0)
        self.window.add(vbox)
        self.window.show_all()

    def init_file_chooser(self):
        self.file_chooser = Gtk.FileChooserDialog(title="File Chooser",
            parent=self.window, action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
              Gtk.STOCK_OK, Gtk.ResponseType.OK))

    def init_commands(self):
        self.commands = {'file quit': 'Gtk.main_quit',
            'file open': 'self.file_open',
            'file save': 'self.file_save',
            'file save as': 'self.file_save_as',
            'show commands': 'self.show_commands',
            'editor clear': 'self.clear_edits',
            'clear edits': 'self.clear_edits',
            'file close': 'self.clear_edits',
            'delete': 'self.delete',
            'select': 'self.select',
            'send keys' : 'self.toggle_keys',
            'insert': 'self.insert',
            'go to the end': 'self.done_editing',
            'done editing': 'self.done_editing',
            'scratch that': 'self.scratch_that',
            'back space': 'self.backspace',
            'new paragraph':  'self.new_paragraph',
        }
        self.write_prefs()
        try:
            self.prefsdialog.checkbox.set_active(False)
        except Exception as e:
            print(str(e.args), "in freespeech.init_commands()")

    def init_prefs(self):
        """ Initialize GUI components for prefs dialog. """

        this = self.prefsdialog = Gtk.Dialog("Command Preferences", self.window,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        # "this" is *not* a python keyword, and I like it better than 'me'
        this.set_default_size(200, 300)
        if not os.access(conf_files['cmdjson'], os.R_OK):
            self.init_commands()
        else:
            self.read_prefs()

        this.label = Gtk.Label(_undent_("\
            Double-click to change command wording.\n\
            If new commands don't work click the learn button to train them."))
        this.vbox.pack_start(this.label, False, False, False)
        this.checkbox=Gtk.CheckButton("Restore Defaults")
        this.checkbox.show()
        this.action_area.pack_start(this.checkbox, False, False, 0)
        this.liststore=Gtk.ListStore(str, str)
        this.liststore.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        this.tree=Gtk.TreeView(this.liststore)
        editable = Gtk.CellRendererText()
        fixed = Gtk.CellRendererText()
        editable.set_property('editable', True)
        editable.connect('edited', self.edited_cb)
        this.connect("show", self.prefs_expose)
        this.liststore.clear()
        for key, value in list(self.commands.items()):
            this.liststore.append([key, eval(value).__doc__])
        this.connect("response", self.prefs_response)
        this.connect("delete_event", self.prefs_response)
        column = Gtk.TreeViewColumn("Spoken command",editable,text=0)
        column.set_min_width(200)
        this.tree.append_column(column)
        column = Gtk.TreeViewColumn("What it does",fixed,text=1)
        this.tree.append_column(column)
        this.vbox.pack_end(this.tree, False, False, 0)
        this.label.show()
        this.tree.show()
        self.commands_old = self.commands
        this.show_all()

    def prefs_expose(self, me, event):
        """ callback when prefs window is shown """
        # populate commands list with documentation
        me.liststore.clear()
        for command_name,command in iter(self.cmds):
            for phrase in command["training_phrases"]:
                me.liststore.append([command_name,phrase])
                print(command_name,phrase,sep="  --  ")

    def write_prefs(self):
        """ write command list to file """
        try:
            with open(conf_files['cmdjson'], mode='w') as f:
                f.write(json.dumps(self.commands))
        except Exception as e:
            no,msg = e.args
            self.err.show(errormsg = no + ": " + msg
                + "\n...Occurred in freespeech.write_prefs() while writing JSON.")
        try:
            with open(conf_files['cmdtext'], mode='w') as f:
                for j in list(self.commands.keys()):
                    f.write('<s> '+j+' </s>\n')
        except Exception as e:
            no,msg = e.args
            self.err.show(errormsg = no + ": " + msg
                + "\n...Occurred in freespeech.write_prefs() while writing text.")

    def read_prefs(self):
        try:
            """ read command list from file """
            with open(conf_files["cmdjson"], mode='r') as f:
                self.commands=json.loads(f.read())
        except OSError as e:
            no,msg = e.args
            self.err.show(errormsg = no + ": " + msg + "\n...Occurred in read_prefs()",
                severity=FATAL)

    def prefs_response(self, me, event):
        """ make prefs dialog non-modal by using response event
            instead of run() method, which waited for input """
        if me.checkbox.get_active():
            # Copy current vocab to commands.json.bak if exists.
            if (os.access(conf_files["commands.json"],os.R_OK)):
                shutil.copy(conf_files["commands.json"],os.path.join(confdir,"commands.json.bak"))
            # Note that this only creates one level of backup. If you go to the preferences menu and
            # choose "restore defaults" twice, it will overwrite the backup with the defaults as well.
            self.init_commands()
        else:
            if event!=Gtk.ResponseType.OK:
                self.cmds = self.commands_old
            else:
                self.write_prefs()
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

    def show_commands(self, argument=None):
        """ show these command preferences """
        me=self.prefsdialog
        self.commands_old = self.commands
        me.show_all()
        me.present()
        return True # command completed successfully!

    def learn_new_words(self, button):
        """ Learn new words, jargon, or other language

          1. Add the word(s) to the dictionary, if necessary.
          2. Type or paste sentences containing the word(s).
          2. Use the word(s) differently in at least 3 sentences.
          3. Click the "Learn" button. """

        # prepare a text corpus from the textbox
        corpus = self.expand_punctuation(
            corpus = self.prepare_corpus(txt=self.textbuf, bounds=self.textbuf.get_bounds())
        )

        # append it to the language reference
        try:
            with open(conf_files["lang_ref"], mode='a+') as f:
                for line in corpus:
                    if line:
                        f.write(line + '\n')
        except FileNotFoundError as e:
            num,msg=e.args
            self.err.show(errormsg=num + ": " + msg, severity=FATAL)
        except PermissionError as e:
            num,msg=e.args
            self.err.show(errormsg=num + ": " + msg, severity=FATAL)

        # cat command
        if platform.system()=='Windows':
            catcmd = 'type '
        else:
            catcmd = 'cat '

        # compile a vocabulary
        # http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html#text2wfreq
        self.logger.log_message("Compiling vocabulary and saving to file.")
        try:
            subprocess.check_call(catcmd + (conf_files["cmdtext"] + ' ')*4
                + conf_files["lang_ref"]
                + '|text2wfreq -verbosity 2 |wfreq2vocab -top 20000 -records 100000 > '
                + conf_files["vocab"], shell=True)
        # this line adds the cmdtext list 4 times to increase likelyhood over lang_ref.
        # not sure if that's the best way to do things, but it seems to work.
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg= 'Trouble writing ' + conf_files["vocab"] + ": " + msg,
                severity=FATAL)
        # update the idngram\
        # http://www.speech.cs.cmu.edu/SLM/toolkit_documentation.html#text2idngram
        self.logger.log_message("Updating idngram based on the new vocabulary")
        try:
            subprocess.check_call('text2idngram -vocab ' + conf_files["vocab"] + ' -n 3 < '
                + conf_files["lang_ref"] + ' > ' + conf_files["idngram"], shell=True)
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg= 'Trouble writing ' + conf_files["idngram"] + ": " + msg,
                severity=FATAL)

        # (re)build arpa language model
        # http://drupal.cs.grinnell.edu/~stone/courses/computational-linguistics/ngram-lab.html
        self.logger.log_message("Rebuilding arpa language model")
        try:
            subprocess.check_call('idngram2lm -idngram -n 3 -verbosity 2 '
                + conf_files["idngram"] + ' -vocab ' + conf_files["vocab"]
                + ' -arpa ' + conf_files["arpa"] + ' -vocab_type 1'
                ' -good_turing', shell=True)
        except subprocess.CalledProcessError as e:
            num,msg = e.args
            self.err.show(errormsg='Trouble writing ' + conf_files["arpa"] + ": " + msg)

        # convert to dmp
        if subprocess.call('sphinx_lm_convert -i ' + conf_files["arpa"] + \
            ' -o ' + conf_files["dmp"] + ' -ofmt dmp', shell=True):
            self.err.show(errormsg='Trouble writing ' + conf_files["dmp"])
        self.init_audio_input()

    def init_audio_input(self):
        with self.mike as m:
            self.wreck.adjust_for_ambient_noise(m)
        self.stop_listening = self.wreck.listen_in_background(self.mike, self.final_result)

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
                f.write(self.textbuf.get_text(self.bounds[0], self.bounds[1]))
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
            self.start_listening()
        else:
            button.set_label("Speak")
            self.snore()

    def toggle_echo(self, button):
        """ echo keystrokes to the desktop

        todo refactor this function and checks for the "echo" attr to be more readable.
        (but it should technically function as is so later...)"""
        if not button.get_active():
            button.set_label("Send keys")
            button.set_active(False)
        else:
            button.set_label("Stop sending")
            button.set_active(True)

    def toggle_keys(self):
        """ echo keystrokes to the desktop """
        self.echo_keys_button.set_active(True - self.echo_keys_button.get_active())
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
        if (starting or re.match(".*[.?!:]", lastchars)) and len(txt) > 1:
            txt = txt[0].capitalize() + txt[1:]
        # add space to beginning if necessary
        if (txt and re.match(r"[^.?!:,\-\"';^@]", txt[0]) and len(lastchars)
                and lastchars[-1] != " " and not starting):
            txt = " " + txt
        # add space to end if necessary
        # abort if text selected
        if not self.textbuf.get_selection_bounds():
            if len(nextchar) and (nextchar != " "):
                txt = txt + " "
        return txt

    def expand_punctuation(corpus):
        """ tweak punctuation to match dictionary utterances
            this is now a function (no self use)
         """
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

    def prepare_corpus(txt, bounds):
        txt.begin_user_action()
        text = txt.get_text(bounds[0], bounds[1], True)
        # break on end of sentence
        text    = re.sub(r'(\w[.:;?!])\s+(\w)', r'\1\n\2', text)
        text    = re.sub(r'\n+', r'\n', text)
        corpus  = re.split(r'\n', text)
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
        return corpus

    def start_listening(self, mike=None, wreck=None):
        if mike is None:
            mike = self.mike
        if wreck is None:
            wreck = self.wreck
        with mike as source:
            self.logger.log_message("Listening on source " + str(source), DEBUG)
            wreck.adjust_for_ambient_noise(source)

        self.snore = wreck.listen_in_background(mike, self.final_result)
        # snore ^^ is a method that can be called to stop wreck/mike from listening.


    def interpret(self, audio, wreck, engine, logger):
        logger.log_message("Interpreting audio...")
        try:
            if engine is 'pocketsphinx':
                return wreck.recognize_sphinx(audio)
            elif engine is 'gv':
                return wreck.recognize_google(audio)
            # etc engines todo
            else:
                raise ValueError(engine)
        except speech_recognition.UnknownValueError:
            logger.log_message("Nothing understood", WARN)
            return False
        except speech_recognition.RequestError as error:
            logger.log_message("Sphinx error: {0}".format(error), ERROR)
            return False
        except ValueError as err:
            logger.log_message("Invalid engine specified" + engine, ERROR)
            return False


    def final_result(self, wreck, audio):
        """Insert the final result into the textbox."""
        hypothesis = self.interpret(audio, self.wreck, ENGINE, self.logger)
        self.logger.log_message("Received text is " + hypothesis)
        if not hypothesis:
            self.err.show_msg("Invalid engine response. See the log for errors.")
        # All this stuff appears as one single action
        self.textbuf.begin_user_action()
        self.text.set_tooltip_text(hypothesis)
        # get bounds of text buffer
        self.bounds = self.textbuf.get_bounds()
        # Fix punctuation
        hypothesis = self.collapse_punctuation(hypothesis, \
        self.bounds[1].starts_line())
        # handle commands
        if not self.do_command(hypothesis):
            self.textbuf.delete_selection(True, self.text.get_editable())
            self.textbuf.insert_at_cursor(hypothesis)
            # send keystrokes to the desktop?
            if self.echo_keys_button.get_active():
                send_string(hypothesis)
                display.sync()
            self.logger.log_message(hypothesis + " executed.")
        ins = self.textbuf.get_insert()
        itera = self.textbuf.get_iter_at_mark(ins) # iter is a python keyword
        # @ Henry Kroll WTF does this do?
        self.text.scroll_to_iter(itera, 0, False, 0.5, 0.5)
        self.textbuf.end_user_action()

    def do_command(self, cmd):
        cmd.strip()
        cmd.lower()
        if cmd in self.commands:
            return eval(self.commands[cmd])
        return False
    """Process spoken commands"""
    def clear_edits(self):
        """ close file and start over without saving """
        self.textbuf.set_text('')
        self.open_filename = ''
        self.window.set_title("FreeSpeech")
        self.undo = []
        return True # command completed successfully!
    def backspace(self):
        """ delete one character """
        start = self.textbuf.get_iter_at_mark(self.textbuf.get_insert())
        self.textbuf.backspace(start, False, True)
        return True # command completed successfully!
    def select(self, argument=None):
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
    def delete(self, argument=None):
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
    def insert(self, argument=None):
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
    def scratch_that(self, command=None):
        """ erase recent text """
        self.bounds = self.textbuf.get_bounds()
        if self.undo:
            scratch = self.undo.pop(-1)
            search_back = self.bounds[1].backward_search( \
                scratch, Gtk.TextSearchFlags.TEXT_ONLY)
            if search_back:
                self.textbuf.select_range(search_back[0], search_back[1])
                self.textbuf.delete_selection(True, self.text.get_editable())
                if self.echo_keys_button.get_active():
                    b = "".join(["\b" for x in range(0,len(scratch))])
                    send_string(b)
                    display.sync()
                return True # command completed successfully!
        return False
    def new_paragraph(self):
        """ start a new paragraph """
        self.textbuf.insert_at_cursor('\n')
        if self.echo_keys_button.get_active():
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
    title       = "Error"
    parent      = None
    dialogFlags = Gtk.DialogFlags.MODAL
    buttons     = 0
    label       = Gtk.Label("Nice label")

    def __init__(self, title="Error", parent=None, dialogFlags=Gtk.DialogFlags.MODAL,
            buttons=(Gtk.STOCK_OK, Gtk.ResponseType.OK)):
        self.logger = LogRecorder()
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

    def show_msg(self, severity=NORMAL, parent=None, errormsg="no error message has been included"):
        if parent is None:
            parent = self
        if severity is LOW:
            self.logger.log_message(errormsg, ERROR)
        elif severity is FATAL:
            self.label.set_text(errormsg)
            self.run()
            self.hide()
            exit(ERROR)
        else:    # Normal severity
            self.label.set_text(errormsg)
            self.run()
            self.hide()
            self.set_defaults()

    # getters and setters
    def set_defaults(self):
        self.set_title()
        self.set_flags()
        self.set_buttons()
    def set_title(self,title="Error"):
        self.title = title
    def set_buttons(self, buttons=(Gtk.STOCK_OK,Gtk.ResponseType.OK)):
        self.buttons = buttons
    def set_flags(self,flags=Gtk.DialogFlags.MODAL):
        self.dialogFlags = flags
    def set_parent(self, parent=None):
        self.parent = parent
    def get_title(self):
        return self.title
    def get_buttons(self):
        return self.buttons
    def get_flags(self):
        return self.dialogFlags

class Wreckognizer(speech_recognition.Recognizer):
    """ A subclass of the Recognizer class with the purpose of reimplementing `recognize_sphinx()`
        with the option acceptance of custom acoustic, language, and phoneme models. """
    def __init__(self):
        super().__init__()

    def recognize_sphinx(self, audio_data, language='en-US', keyword_entries=None, grammar=None,
            show_all=False, acoustic_model=None, language_model=None, phoneme_model=None,
            base_dir=None):
        assert isinstance(audio_data, AudioData),                                                  \
            "Given parameter 'audio_data' must be audio data (of AudioData type)"
        assert isinstance(language, str) or language is None,                                      \
            "Language setting must be a string."
        assert isinstance(acoustic_model, str) or acoustic_model is None,                          \
            "acoustic_model filename must be a string."
        assert isinstance(language_model, str) or language_model is None,                          \
            "language_model filename must be a string."
        assert isinstance(phoneme_model, str) or phoneme_model is None,                            \
            "phoneme_model filename must be a string."
        assert (isinstance(base_dir, str) or base_dir is None),                                    \
            "base directory path must be formatted as a string"
        assert keyword_entries is None or all(isinstance(keyword, (type(""), type(u'')))           \
            and 0 <= sensitivity <= 1 for keyword, sensitivity in keyword_entries), _undent_("\
            ``keyword_entries`` must be ``None`` or a list of pairs of strings and numbers between \
            0 and 1")
        # Holy crap that's a complicated line ^^
        try:
            from pocketsphinx import pocketsphinx, Jsgf, FsgModel
        except ImportError:
            raise RequestError("missing PocketSphinx module: ensure that PocketSphinx is set up correctly.")
        except ValueError:
            raise RequestError("bad PocketSphinx installation; try reinstalling PocketSphinx version 0.0.9 or better.")
        if not hasattr(pocketsphinx, "Decoder") or not hasattr(pocketsphinx.Decoder, "default_config"):
            raise RequestError("outdated PocketSphinx installation; ensure you have PocketSphinx version 0.0.9 or better.")
        if base_dir is None:
                base_dir = os.path.join(pocketsphinx_files_dir)
        if not os.path.isdir(base_dir):
            raise RequestError("missing PocketSphinx language data directory: \"{}\"".format(base_dir))
        if acoustic_model is None: # set to default for SpeechRecognition
            acoustic_parameters_directory = base_dir
        else:   #   the acoustic model file has been defined.
            acoustic_parameters_directory = acoustic_model
        if not os.path.isdir(acoustic_parameters_directory):
            raise RequestError("missing PocketSphinx language model parameters directory: \"{}\"".format(acoustic_parameters_directory))
        if language_model is None: # set to default for SpeechRecognition
            language_model_file = os.path.join(base_dir, "FreezePeach")
        else:   #   the language model file has been defined
            language_model_file = language_model
        if not os.path.isfile(language_model_file):
            raise RequestError("missing PocketSphinx language model file: \"{}\"".format(language_model_file))
        if phoneme_model is None: # set to default for SpeechRecognition
            phoneme_dictionary_file = CONF_FILES['dic']
        else:   #   the phoneme model file has been defined
            phoneme_dictionary_file = phoneme_model
        if not os.path.isfile(phoneme_dictionary_file):
            raise RequestError("missing PocketSphinx phoneme dictionary file: \"{}\"".format(phoneme_dictionary_file))

        # everything else is verbatim from the original Recognizer() class

        # create decoder object
        config = pocketsphinx.Decoder.default_config()
        config.set_string("-hmm", acoustic_parameters_directory)  # set the path of the hidden Markov model (HMM) parameter files
        config.set_string("-lm", language_model_file)
        config.set_string("-dict", phoneme_dictionary_file)
        config.set_string("-logfn", os.devnull)  # disable logging (logging causes unwanted output in terminal)
        decoder = pocketsphinx.Decoder(config)

        # obtain audio data
        raw_data = audio_data.get_raw_data(convert_rate=16000, convert_width=2)  # the included language models require audio to be 16-bit mono 16 kHz in little-endian format

        # obtain recognition results
        if keyword_entries is not None:  # explicitly specified set of keywords
            with PortableNamedTemporaryFile("w") as f:
                # generate a keywords file - Sphinx documentation recommendeds sensitivities between 1e-50 and 1e-5
                f.writelines("{} /1e{}/\n".format(keyword, 100 * sensitivity - 110) for keyword, sensitivity in keyword_entries)
                f.flush()

                # perform the speech recognition with the keywords file (this is inside the context manager so the file isn;t deleted until we're done)
                decoder.set_kws("keywords", f.name)
                decoder.set_search("keywords")
                decoder.start_utt()  # begin utterance processing
                decoder.process_raw(raw_data, False, True)  # process audio data with recognition enabled (no_search = False), as a full utterance (full_utt = True)
                decoder.end_utt()  # stop utterance processing
        elif grammar is not None:  # a path to a FSG or JSGF grammar
            if not os.path.exists(grammar):
                raise ValueError("Grammar '{0}' does not exist.".format(grammar))
            grammar_path = os.path.abspath(os.path.dirname(grammar))
            grammar_name = os.path.splitext(os.path.basename(grammar))[0]
            fsg_path = "{0}/{1}.fsg".format(grammar_path, grammar_name)
            if not os.path.exists(fsg_path):  # create FSG grammar if not available
                jsgf = Jsgf(grammar)
                rule = jsgf.get_rule("{0}.{0}".format(grammar_name))
                fsg = jsgf.build_fsg(rule, decoder.get_logmath(), 7.5)
                fsg.writefile(fsg_path)
            else:
                fsg = FsgModel(fsg_path, decoder.get_logmath(), 7.5)
            decoder.set_fsg(grammar_name, fsg)
            decoder.set_search(grammar_name)
            decoder.start_utt()
            decoder.process_raw(raw_data, False, True)  # process audio data with recognition enabled (no_search = False), as a full utterance (full_utt = True)
            decoder.end_utt()  # stop utterance processing
        else:  # no keywords, perform freeform recognition
            decoder.start_utt()  # begin utterance processing
            decoder.process_raw(raw_data, False, True)  # process audio data with recognition enabled (no_search = False), as a full utterance (full_utt = True)
            decoder.end_utt()  # stop utterance processing

        if show_all: return decoder

        # return results
        hypothesis = decoder.hyp()
        if hypothesis is not None: return hypothesis.hypstr
        raise UnknownValueError()  # no transcriptions available
class LogRecorder():
    LOGLVL = ["LOG", "ERROR", "SUBPROCESS_MESSAGE", "DEBUG", "WARN"]
    """ handles logging of messages."""
    def __init__(self):
        pass
    def log_message(self, message, level=LOG):
        """" There are five log-levels, defined at the top of the file, as follows:
                0: LOG
                1: ERROR
                2: SUBPROCESS_FAILURE
                3: DEBUG
                4: WARN
            Currently these levels all function the same: they print to stdout.
            However, it would be trivial to filter these using if/elif/else
            below.
        """
        print("FreezePeach: ", self.LOGLVL[level], " -- ", message)

class Interface():
    def __init__(self):
        doc = dominate.document(title='FreeSpeech (engine-independent continuous speech recogntion')
        with doc.head as h:
            self.define_header(h)
        with doc as dcmnt:
            self.define_preamble(dcmnt)
        return doc
    def define_header(self, head):
        #link(rel='sylesheet', href='style.css') Uncomment when stylesheet is defined
        pass
    def define_preamble(self, doc):
        with doc:
            with div(id='header').add(h1()):
                p('FreeSpeech (engine-independent continuous speech recogntion')
            with div():
                attr(cls='body')
                p('This is an example of speech synthesis in Android.')
if __name__ == "__main__":
    app = FreeSpeech()
    Gtk.main()
