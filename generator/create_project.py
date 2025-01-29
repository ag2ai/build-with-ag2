from utils import ProjectCreator


def main():
    user_input = input("Enter the project name: ")
    project = ProjectCreator(user_input)
    """Runs all project setup steps."""
    project.create_folder()
    project.initialize_uv()
    project.install_dependencies()
    project.copy_jupyter_notebook()
    project.create_readme()
    project.rename_hello_to_main()
    project.copy_config_file()
    print(f"Project '{project.name}' created successfully...")


if __name__ == "__main__":
    main()
