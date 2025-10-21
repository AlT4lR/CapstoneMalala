#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt```

#### D. Create a `.gitignore` File
You should not commit secrets or temporary files to your Git repository. Create a `.gitignore` file in your root directory (`Capstone/`).

**File: `.gitignore`**