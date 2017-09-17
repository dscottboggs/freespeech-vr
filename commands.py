import re, json, subprocess, os, shutil
class commands():
    cmd_list        = []
    quick_ref       = []
    confdir         = os.path.join("/", "etc", "freespeech")
    refdir          = os.path.join("/", "usr", "share", "freespeech")
    commands_json   = os.path.join(confdir,"commands.json")
    parent          = None
    training_phrases= []
    def __init__(self,parent=None):
        cmd_list = load_commands()
        self.parent=parent

    def new_command(name, listen_for, cmd_type, command, description, training_phrases):
        if name is None or listen_for is None or cmd_type is None or command is None or description is None or training_phrases.length() < 1 :
            return "Incomplete command. Command not saved."
        else:
            cmd_str = json.dumps(
                {"Name":name,
                "listen_for":listen_for,
                # todo check valid cmd_type before this
                "cmd_type":cmd_type,
                "command":command,
                "description":description})
            with open('commands.json','w') as cmd_file:
                cmd_list = load_commands()
                cmd_list.append(cmd_str)
                cmd_file.write(cmd_list)
    def load_commands():
        try:
            with open(commands_json,'r') as cmd_file:
                if os.path.getsize(cmd_file) < 1:
                    shutil.copy(os.path.join(refdir,"default_commands.json"), os.path.join(confdir, "commands.json"))
                # copies a default set of commands to the configuration directory from the reference
                # directory if the one in the configuration dir is empty
                return json.loads(cmd_file)
        except OSError:
            try:
                shutil.copy(os.path.join(refdir,"default_commands.json"), os.path.join(confdir,"commands.json"))
            except OSError:
                parent.err.show(errormsg="Cannot create commands.json in /etc/freespeech", severity=parent.FATAL)
    def create_quicker_reference():
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
        for cmd in cmd_list:
            quick_ref.append((cmd["listen_for"], cmd["Name"]))
    def search(heard_str):
        valid = False
        for c,d in quick_ref:
            if c.matches(heard_str):
                valid=True
                find_cmd(d)
        # valid should have been changed to True if a valid command was found 
        if valid=False:
            command_not_found()

    def find_cmd(name):
        for cmd in cmd_list:
            if name=cmd["Name"]:
                execute(cmd_type=cmd["cmd_type"],command=cmd["command"])

    def execute(cmd_type, command):
        if cmd_type is "PYTHON":
            exec(command)
        #elif cmd_type is "PYTHON2":
        #   idk how to do this. TODO, or fuck it?
        elif cmd_type is "BASH":
            successful = subprocess.check_call(command,shell=True)
        elif cmd_type is "REST":
            pass
        elif cmd_type is "SAY":
            pass
        elif cmd_type is "PRINT":
            pass
        elif cmd_type is "META":
            metacommmand(command)
        else:
            command_type_not_found
    def command_not_found():
        pass
    def command_type_not_found():
        pass

    def metacommand(command):
        # If there's a better way to do this I'm open to it.
        if (command == "quit_freespeech"):
            parent.Gtk.main_quit()
        elif (command == "file_open"):
            parent.file_open()
        elif (command == "file_save_as"):
            parent.file_save_as()
        elif (command == "file_save"):
            parent.file_save()
        elif (command == "freespeech_help"):
            parent.show_commands()

        