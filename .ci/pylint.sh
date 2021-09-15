#!/bin/sh

echo "Doing pylint..."
bool=false
# explicitly set IFS to contain only a line feed
IFS='
'
filelist="$(find . -type f ! -name "$(printf "*\n*")")"
for line in $filelist; do
  if echo "$line" | grep -E -q ".*\.\/.*\.py$" ; then
    if ! grep -Eq "$line" ".ci/python_accepted"; then
      if ! pylint -d "invalid-name" -d "missing-class-docstring" -d "missing-module-docstring" -d "missing-function-docstring" --extension-pkg-whitelist=cv2 --init-hook='import sys; sys.path.append("../octoprint_OctoPNP")' "$line"; then
        bool=true
      fi
    fi
  fi
done
if $bool; then
  exit 1
else
  echo "No pylint errors found."
fi

exit 0
