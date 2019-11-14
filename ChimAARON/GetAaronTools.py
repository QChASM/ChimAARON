import Tkinter
import Tix
import sys
import os
import ChimAARON
import chimera

from chimera.baseDialog import ModelessDialog
from tkFileDialog import askdirectory

class GetAaronToolsDialog(ModelessDialog):
    title = "Get or Backport AaronTools"
    
    buttons = ("Close",)
    help = ("tutorials/setupGuide.html", ChimAARON)

    def __init__(self):
        if sys.version_info < (3,):
            self.NEED_FUTURE = True
        else:
            self.NEED_FUTURE = False
        
        self.CHECK_FOR_AARONTOOLS()
        
        try:
            import pip
            if int(pip.__version__.split('.')[0]) < 19:
                self.HAS_PIP = False
            else:
                self.HAS_PIP = True
        
        except ImportError:
            self.HAS_PIP = False
    
        print(self.NEED_FUTURE)
        print(self.HAS_AARONTOOLS)
        print(self.IMPORTED_AARONTOOLS)
        print(self.NEED_PIP)
        print(self.HAS_PIP)
        
        ModelessDialog.__init__(self)
    
    def CHECK_FOR_AARONTOOLS(self):
        try:
            import AaronTools
            self.HAS_AARONTOOLS = True
            for f in os.listdir(os.path.dirname(AaronTools.__file__)):
                if f.endswith('.py'):
                    exec "import AaronTools.%s" % ".".join(f.split('.')[:-1])
                    print(f)
                            
            self.IMPORTED_AARONTOOLS = True
        
        except SyntaxError:
            self.HAS_AARONTOOLS = True
            self.IMPORTED_AARONTOOLS = False
            
        except ImportError:
            if not hasattr(self, "HAS_AARONTOOLS") and not self.HAS_AARONTOOLS:
                self.HAS_AARONTOOLS = False
            
            self.IMPORTED_AARONTOOLS = False
        
        if self.NEED_FUTURE or not self.HAS_AARONTOOLS:
            try:
                import pip
                self.NEED_PIP = False
            
            except ImportError:
                self.NEED_PIP = True
    
    def fillInUI(self, parent):
        from ChimAARON.prefs import ENVIRONMENT
        
        envPrefs = chimera.preferences.preferences.get('ChimAARON', ENVIRONMENT)
        if 'AARONLIB' in envPrefs:
            arnlib = envPrefs['AARONLIB']
        else:
            arnlib = None
            
        self.envDisplayArea = Tkinter.LabelFrame(parent, text="AaronTools Environment")
        self.envDisplayArea.grid(row=0, column=0, sticky='nsew')
        self.envDisplayArea.rowconfigure(0, weight=1)
        self.envDisplayArea.columnconfigure(0, weight=1)
        
        row = 0
        
        self.envChanges = Tkinter.Label(self.envDisplayArea, text="You'll have to restart Chimera for environment changes to take effect")
        self.envChanges.grid(row=row, column=0, sticky='new')
        
        row += 1
        
        self.AARONLIBButton = Tkinter.Button(self.envDisplayArea, anchor='w', text="set AARONLIB location", command=self.arnlibSelect)
        self.AARONLIBButton.grid(row=row, column=0, sticky='w')

        
        self.envLabel = Tkinter.Label(self.envDisplayArea, anchor='w', text="Personal AaronTools Library Location: %s" % arnlib)
        self.envLabel.grid(row=row, column=1, sticky='ew')
        
        row += 1
        
        #display backport/setup instructions
        self.inputDisplayArea = Tkinter.LabelFrame(parent, text="Dependencies")
        self.inputDisplayArea.grid(row=1, column=0, sticky='nsew')
        self.inputDisplayArea.rowconfigure(0, weight=1)
        self.inputDisplayArea.columnconfigure(1, weight=1)
        
        row = 0
        
        self.installPipButton = Tkinter.Button(self.inputDisplayArea, text="install pip with ensurepip and update pip", command=self.installPip)
        self.installPipButton.grid(row=row, column=0, sticky='sew')
        
        row += 1
        
        self.installDependenciesButton = Tkinter.Button(self.inputDisplayArea, text="install dependencies", command=self.installDependencies)
        self.installDependenciesButton.grid(row=row, column=0, sticky='new')
        
        row += 1
        
        self.backportButton = Tkinter.Button(self.inputDisplayArea, text="pasteurize AaronTools", command=self.backportAaronTools)
        self.backportButton.grid(row=row, column=0, sticky='new')        
        self.backportButton.config(state="disabled")

        row += 1
        
        self.moreBackportsButton = Tkinter.Button(self.inputDisplayArea, text="fix misc. backporting", command=self.doAdditionalBackports)
        self.moreBackportsButton.grid(row=row, column=0, sticky='new')
        self.moreBackportsButton.config(state="disabled")
        
        row += 1
        
        self.inputDisplay = Tkinter.Text(self.inputDisplayArea, wrap='word')
        self.inputDisplay.grid(row=0, column=1, rowspan=row, sticky='nsew')
        self.inputScroll = Tkinter.Scrollbar(self.inputDisplayArea, command=self.inputDisplay.yview)
        self.inputScroll.grid(row=0, column=2, rowspan=row, sticky='nsew')
        self.inputDisplay.rowconfigure(0, weight=1)
        self.inputDisplay.columnconfigure(0, weight=1)
        self.inputDisplay['yscrollcommand'] = self.inputScroll.set  
        
        readme = """If you have installed ChimAARON from the QChASM GitHub alongside the ChimAARON-compatible AaronTools, you do not need to backport AaronTools.

To install dependencies, you'll have to bootstrap/install pip first. This can be done by pressing the 'install pip with ensurepip and update pip' button to the left. 

Once pip is installed, you will be able to install the AaronTools dependencies (future and cclib) with the 'install dependencies' button. 



Fresh installations of AaronTools need to be backported to Python 2 for ChimAARON to work. Backporting is a two-step process: first, run the pasteurize script that was installed with `future`, and then fix random things that pasteurize doesn't. Please wait for pasteurize to finish before running 'fix misc. backporting'.

After all of that is complete, ChimAARON tools should function the next time you start Chimera."""
        
        self.inputDisplay.delete("1.0", Tkinter.END)
        self.inputDisplay.insert(Tkinter.END, readme)
        
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        
    def installPip(self):
        from chimera import replyobj
        import ensurepip
        import subprocess
        
        try:
            ensurepip.bootstrap()
        except AttributeError as e:
            replyobj.warning("encountered an error while bootstrapping pip:\n%s\n \
This error can occur when an old version of ensurepip tries to run a newer version of pip. \
We'll ignore this error and proceed with updating the current version of pip" % e)
        
        proc = subprocess.Popen([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()
        replyobj.status(out[0])
        print(out[0])
        
            
    def installDependencies(self):
        from chimera import replyobj
        import subprocess
        import shutil
        
        print('installing future...')
        replyobj.status('installing future...')
        proc = subprocess.Popen([sys.executable, '-m', 'pip', 'install', 'future'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()
        replyobj.status(out[0])
        print(out[0])
        if out[1]:
            replyobj.warning(out[1])
        
        print('installing cclib...')
        replyobj.status('installing cclib...')
        proc = subprocess.Popen([sys.executable, '-m', 'pip', 'install', 'cclib'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()
        replyobj.status(out[0])
        print(out[0])
        if out[1]:
            replyobj.warning(out[1])        
        
    def backportAaronTools(self):
        import subprocess
        from chimera import replyobj
        import AaronTools
        
        AaronTools_dir = os.path.dirname(AaronTools.__file__)
        
        print("AaronTools found in %s" % AaronTools_dir)
        replyobj.status("AaronTools found in %s" % AaronTools_dir)
        
        scripts_dir = os.path.join(os.path.dirname(sys.executable), "Scripts")
        for script in os.listdir(scripts_dir):
            if "pasteurize" in script:
                pasteurize_exe = os.path.join(scripts_dir, script)
        
        proc = subprocess.Popen([pasteurize_exe, '-w', AaronTools_dir], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.communicate()
        replyobj.status(out[0])
        print(out[0])
        if out[1]:
            replyobj.warning(out[1])
    
    def doAdditionalBackports(self):
        import AaronTools
        from chimera import replyobj
        from ChimAARON.backporter import backporter_main

        AaronTools_dir = os.path.dirname(AaronTools.__file__)
        
        print("AaronTools found in %s" % AaronTools_dir)
        replyobj.status("AaronTools found in %s" % AaronTools_dir)
        
        backporter_main(AaronTools_dir)
        
        utils_init = os.path.join(AaronTools_dir, 'utils', '__init__.py')
        
        if not os.path.exists(utils_init):
            with open(utils_init, 'a'):
                os.utime(utils_init, None)
            
    def arnlibSelect(self):
        from ChimAARON.prefs import prefs, ENVIRONMENT
        from copy import deepcopy
        from chimera import replyobj
        
        if 'AARONLIB' in prefs[ENVIRONMENT]:
            libPref = prefs[ENVIRONMENT]['AARONLIB']
        else:
            libPref = None
        
        arnlib = askdirectory(initialdir=libPref, title="Select AARONLIB directory")
        
        if arnlib:
            envPrefs = deepcopy(prefs[ENVIRONMENT])
            envPrefs['AARONLIB'] = arnlib
            prefs[ENVIRONMENT] = envPrefs
            
            libs = ['RingFrags', 'Subs', 'Ligands', 'TS_geoms']
            
            for lib in libs:
                libDir = os.path.join(arnlib, lib)
                if not os.path.exists(libDir):
                    os.makedirs(libDir)

            replyobj.status("set AARONLIB to %s and created library directories" % arnlib)
            self.envLabel.config(text="Personal AaronTools Library Location: %s" % arnlib)
        