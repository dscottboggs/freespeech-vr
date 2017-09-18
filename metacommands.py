from freespeech import * # This is for metacommands, it basically is just an extension of FreeSpeech and can act on all its methods and arguments. Perhaps this could be revised.
class metacommands():
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
    
    def freespeech_help():
        """ show these command preferences """
        me=self.prefsdialog
        self.commands_old = self.cmds
        me.show_all()
        me.present()
        return True # command completed successfully!
