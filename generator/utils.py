import os
import subprocess
import shutil
from readme import create_readme


class ProjectCreator:

    def __init__(self, name):
        self.name = self.normalize_name(name)
        self.folder = self.name
        self.dev_dependencies = ["ipykernel"]
        self.dependencies = ["ag2"]
        self.template_notebook = os.path.join(
            os.path.dirname(__file__), "template.ipynb"
        )

    def normalize_name(self, name):
        """Converts a given name into a normalized format: 'this-is-my-name'."""
        return "-".join(name.lower().split())

    def create_folder(self):
        """Creates a folder with the given name."""
        os.makedirs(self.folder, exist_ok=True)

    def initialize_uv(self):
        """Initializes a virtual environment using `uv init` inside the specified folder."""
        subprocess.run(["uv", "init"], cwd=self.folder)

    def install_dependencies(self):
        """Installs the required dependencies inside the virtual environment."""
        for package in self.dev_dependencies:
            subprocess.run(["uv", "add", "--dev", package], cwd=self.folder)
        for package in self.dependencies:
            subprocess.run(["uv", "add", package], cwd=self.folder)

    def copy_jupyter_notebook(self):
        """Copies the Jupyter notebook template and ensures the correct kernel metadata is set."""
        notebook_path = os.path.join(self.folder, f"{self.name}.ipynb")

        if not os.path.exists(self.template_notebook):
            print(f"Warning: Template notebook {self.template_notebook} not found!")
            return

        # Copy the template
        shutil.copy(self.template_notebook, notebook_path)

    def rename_hello_to_main(self):
        """Renames 'hello.py' to 'main.py' inside the project folder."""
        hello_path = os.path.join(self.folder, "hello.py")
        main_script_path = os.path.join(self.folder, "main.py")

        if os.path.exists(hello_path):
            os.rename(hello_path, main_script_path)
        else:
            print(f"Error: 'hello.py' not found in {self.folder}")

    def create_readme(self):
        create_readme(self)

    def copy_config_file(self):
        """Copies the template_OAI_CONFIG_LIST file and renames it to OAI_CONFIG_LIST in the project folder."""
        template_config_path = os.path.join(
            os.path.dirname(__file__), "template_OAI_CONFIG_LIST"
        )
        config_path = os.path.join(self.folder, "OAI_CONFIG_LIST")
        destination_template_path = os.path.join(self.folder, "OAI_CONFIG_LIST_sample")

        if not os.path.exists(template_config_path):
            print(f"Warning: Template config file {template_config_path} not found!")
            return

        shutil.copy(template_config_path, config_path)
        shutil.copy(template_config_path, destination_template_path)
