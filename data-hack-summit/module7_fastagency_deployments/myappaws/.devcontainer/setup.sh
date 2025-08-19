# update pip
pip install --upgrade pip

# install dev packages
pip install -e ".[dev]"

# install pre-commit hooks
pre-commit install

# install AWS CLI
# nosemgrep: bash.curl.security.curl-pipe-bash.curl-pipe-bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# check OPENAI_API_KEY environment variable is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo
    echo -e "\033[33mWarning: OPENAI_API_KEY environment variable is not set.\033[0m"
    echo
fi
