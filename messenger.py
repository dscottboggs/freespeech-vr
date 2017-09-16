import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
LOW, NORMAL, HIGH, FATAL = 0,1,2,3
SUCCESSFULLY, ERROR, SUBPROCESS_FAILURE = 0,1,2

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
        # Defaults are for error messages.
        self.title=title
        self.parent=parent
        self.dialogFlags=dialogFlags
        self.buttons=buttons
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
            print(errormsg) #simply pushes to stdout, rather than nagging with a popup.
            # Actually, we should probably use something more like notify-send than
            # stdout, as we are no longer writing with the asssumtion that FreeSpeech
            # will be run from a terminal.
        elif severity is HIGH:
            #TODO
            self.label.set_text(errormsg)
            self.run()
            self.hide()
        elif severity is FATAL:
            self.label.set_text(errormsg)
            self.run()
            self.hide()
            exit(ERROR)
        else:    # Normal severity
            self.label.set_text(errormsg)
            self.run()
            self.hide()
    def run(self, parent=None, errormsg="No error message has been included"):
        if parent is None:
            parent=self
        self.label.set_text(errormsg)
        return super().run()