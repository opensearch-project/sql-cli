# Prerequisites Installation Guide

This guide provides detailed installation instructions for all prerequisites needed to run the OpenSearch SQL CLI.

## Git Installation

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install git

# CentOS/RHEL
sudo yum install git

# Fedora
sudo dnf install git

# Arch Linux
sudo pacman -S git
```

**macOS:**
```bash
# Using Homebrew (recommended)
brew install git

# Using Xcode Command Line Tools
xcode-select --install
```

**Verify Installation:**
```bash
git --version
```

## Python 3.12 Installation

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.12 python3.12-pip
```

**Linux (Amazon Linux 2023):**
```bash
sudo dnf install python3.12 python3.12-pip

# Set up alias to use python3.12 as default python3
alias python3=python3.12
# Make alias permanent
echo "alias python3=python3.12" >> ~/.bashrc
source ~/.bashrc
```

**Linux (Amazon Linux 2):**
```bash
# Using pyenv (recommended)
curl https://pyenv.run | bash
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
source ~/.bashrc
pyenv install 3.12.7
pyenv global 3.12.7
```

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python@3.12

# Using pyenv
curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv global 3.12.0
```



**Verify Installation:**
```bash
python3 --version  # Should show Python 3.12.x
python --version   # Should show Python 3.12.x
```

## pip Installation

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-pip

# CentOS/RHEL
sudo yum install python3-pip

# Fedora
sudo dnf install python3-pip

# Arch Linux
sudo pacman -S python-pip
```

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python
# pip comes bundled with Python from Homebrew

# Using get-pip.py (if Python is already installed)
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
```

**Verify pip Installation:**
```bash
pip3 --version
# or
python3 -m pip --version
```

## Java Installation

> **Important**: Java version 21 or higher is required. Java 21 is recommended (especially for Amazon Linux), Java 24 is also supported.

**Linux:**
```bash
# Using SDKMAN (recommended)
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 24-open

# Using package manager
# Ubuntu/Debian
sudo apt update
sudo apt install openjdk-24-jdk

# CentOS/RHEL/Fedora
sudo dnf install java-24-openjdk-devel

# Amazon Linux 2023
sudo dnf update
sudo dnf install java-24-amazon-corretto-devel

# Amazon Linux 2 (manual installation)
wget https://corretto.aws/downloads/latest/amazon-corretto-24-x64-linux-jdk.tar.gz
tar -xzf amazon-corretto-24-x64-linux-jdk.tar.gz
sudo mv amazon-corretto-24.* /opt/corretto-24
sudo ln -sf /opt/corretto-24/bin/java /usr/bin/java
sudo ln -sf /opt/corretto-24/bin/javac /usr/bin/javac
```

**macOS:**
```bash
# Using Homebrew
brew install openjdk@24

# Using SDKMAN
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"
sdk install java 24-open
```

**Verify Installation:**
```bash
java -version
javac -version
```

**Set Java Environment Variables:**

**macOS:**
```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH=$JAVA_HOME/bin:$PATH

# Make permanent
echo 'export JAVA_HOME=$(/usr/libexec/java_home -v 21)' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```

**Linux:**
```bash
# Find your Java installation path
sudo find /usr -name "java" -type f 2>/dev/null | grep bin

# Set JAVA_HOME (replace with your actual Java path)
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk  # or java-21-amazon-corretto.x86_64
export PATH=$JAVA_HOME/bin:$PATH

# Make permanent
echo 'export JAVA_HOME=/usr/lib/jvm/java-21-openjdk' >> ~/.bashrc
echo 'export PATH=$JAVA_HOME/bin:$PATH' >> ~/.bashrc
source ~/.bashrc
```



