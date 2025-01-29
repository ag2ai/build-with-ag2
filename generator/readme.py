import os


def create_readme(self):
    """Creates a README.md file inside the folder with project details."""
    readme_content = f"""# {self.name}

<Overall Description, authorship/references>

## Detailed Description
<More detailed description, any additional information about the use case>

## Installation
<Instructions for installing>

## Running the code
<Code running instructions>

## Contact

For more information or any questions, please refer to the documentation or reach out to us!

- View Documentation at: [https://docs.ag2.ai/docs/Home](https://docs.ag2.ai/docs/Home)
- Reach out to us: [https://github.com/ag2ai/ag2](https://github.com/ag2ai/ag2)
- Join Discord: [https://discord.gg/pAbnFJrkgZ](https://discord.gg/pAbnFJrkgZ)

## License

... <Comply with the license if the use case is modified>
"""
    readme_path = os.path.join(self.folder, "README.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)
