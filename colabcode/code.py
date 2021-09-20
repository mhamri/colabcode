"""base code"""
import os
import pathlib
import subprocess

from pyngrok import ngrok

BASE_FOLDER= pathlib.Path(__file__).parent.resolve()
BASE_FOLDER= os.path.realpath(f"{BASE_FOLDER}/..")
print(f"current folder : ${BASE_FOLDER}")

try:
    COLAB_ENV = True
    from google.colab import drive  # type:ignore
except ImportError:
    COLAB_ENV = False

PIPE = subprocess.PIPE

EXTENSIONS = [
    "ms-python.python",
    "jithurjacob.nbpreviewer",
    "njpwerner.autodocstring",
    "ms-python.vscode-pylance",
    "ms-vscode-remote.remote-wsl",
    "ms-python.anaconda-extension-pack",
    "donjayamanne.githistory",
    "bee.git-temporal-vscode",
    "kiteco.kite",
    "vscode-icons-team.vscode-icons",
]
# "julialang.language-julia"


class ColabCode:
    """[sets up code server on an ngrok link]"""

    def __init__(
        self,
        port=10000,
        password=None,
        mount_drive=False,
        add_extensions=None,
        prompt="powerline-plain",
        get_zsh=False,
    ):
        self.port = port
        self.password = password
        self._mount = mount_drive
        self._prompt = prompt
        self._zsh = get_zsh
        self.url=None
        self.extensions = EXTENSIONS
        if add_extensions is not None and add_extensions != []:
            if isinstance(add_extensions, list) and isinstance(add_extensions[0], str):
                self.extensions += add_extensions
            else:
                raise TypeError(
                    "You need to pass a list of string(s) e.g. ['ms-python.python']"
                )
        self._install_code()
        self._install_extensions()
        # install code-server, then extensions
        # creates the User folder, then transfer settings
        self._settings()
        self._start_server()
        self._run_code()


    def __del__(self):
        ngrok.disconnect(self.url)
        ngrok.kill()

    def _settings(self):
        """install ohmybash and set up code_server settings.json file
        Plus, set up powerline bash prompt
        https://github.com/ohmybash/oh-my-bash
        https://github.com/cdr/code-server/issues/1680#issue-620677320
        """
        ohmybash_filename="install_ohmybash.sh"
        if (not os.path.exists(ohmybash_filename)):
            process= subprocess.run(
                [
                    "wget",
                    "https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh",
                    "-O",
                    ohmybash_filename,
                ],
                stdout=PIPE,
                check=True,
            )
            print(f"wget output: {process}")
        else:
            print(f"{ohmybash_filename} exists. skipping...")

        subprocess.run(["sh", ohmybash_filename], stdout=PIPE, check=True)

        if self._zsh:
            subprocess.run(["sh", "./code_server/get_zsh.sh"], stdout=PIPE, check=True)

        # set bash theme as 'powerline-plain'
        # for undu's theme : `source ~/.powerline.bash` works
        if self._prompt in [
            "powerline-plain",
            "powerline",
            "agnoster",
            "powerline-undu",
        ]:
            subprocess.run(
                ["sh", f"{BASE_FOLDER}/code_server/sed.sh", f"{self._prompt}"],
                stdout=PIPE,
                check=True,
            )

        # either `shell=False` or `cp x y` instead of list
        # https://stackoverflow.com/a/17880895/13070032
        for src, dest in {
            "settings.json": "~/.local/share/code-server/User/settings.json",
            "coder.json": "~/.local/share/code-server/coder.json",
            ".undu-powerline.bash": "~/.powerline.bash",
        }.items():
            subprocess.call(
                f"cp {BASE_FOLDER}/code_server/{src} {dest}",
                stdout=PIPE,
                shell=True,
            )

        # to enable `python -m venv envname`
        # also add nano [vim, tmux (default py2!), ... if needed]
        subprocess.call(
            "apt-get update && apt-get install python3-venv nano",
            stdout=PIPE,
            shell=True,
        )

    def _install_code(self):
        codeserver_filename="code-server-install.sh"
        if not os.path.exists(codeserver_filename):
            subprocess.run(
                ["wget", "https://code-server.dev/install.sh", "-O", codeserver_filename],
                stdout=PIPE,
                check=True,
            )
        else:
            print(f"{codeserver_filename} exists. skipping...")
            
        subprocess.run(["sh", codeserver_filename], stdout=PIPE, check=True)

    def _install_extensions(self):
        """set check as False - otherwise non existing extension will give error"""
        for ext in self.extensions:
            subprocess.run(
                ["code-server", "--install-extension", f"{ext}"], check=False
            )

    def _start_server(self):
        active_tunnels = ngrok.get_tunnels()
        for tunnel in active_tunnels:
            public_url = tunnel.public_url
            ngrok.disconnect(public_url)
        self.url = ngrok.connect(addr=self.port)

        print(f"Code Server can be accessed on: {self.url}")

    def _run_code(self):
        os.system(f"fuser -n tcp -k {self.port}")
        _tele = "--disable-telemetry"
        if self._mount and COLAB_ENV:
            print(drive.mount("/content/drive"))
        if self.password:
            code_cmd = (
                f"PASSWORD={self.password} code-server --port {self.port} {_tele}"
            )
        else:
            code_cmd = f"code-server --port {self.port} --auth none {_tele}"
        with subprocess.Popen(
            [code_cmd],
            shell=True,
            stdout=PIPE,
            bufsize=1,
            universal_newlines=True,
        ) as proc:
            for line in proc.stdout:
                print(line, end="")

    
