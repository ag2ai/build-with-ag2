# update pip
pip install --upgrade pip

# install dev packages
pip install -e ".[dev]"

# install pre-commit hooks
pre-commit install

# install azure CLI
# nosemgrep: bash.curl.security.curl-pipe-bash.curl-pipe-bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# check OPENAI_API_KEY environment variable is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo
    echo -e "\033[33mWarning: OPENAI_API_KEY environment variable is not set.\033[0m"
    echo
fi
