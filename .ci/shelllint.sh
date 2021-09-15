#!/bin/sh

echo "Doing schelllint..."
bool=false
# explicitly set IFS to contain only a line feed
IFS='
'
filelist="$(find . -not \( -path '*/hooks/*' -prune \) -type f ! -name "$(printf "*\n*")")"
for line in $filelist; do
  if echo "$line" | grep -q -E ".*\.sh$" || head -n1 "$line" | grep -q -E "#.*(sh|bash|dash|ksh)$" ; then
    if ! grep -q "$line" ".ci/shell_accepted"; then
      shellcheck -e SC1091 -s sh "$line"
      if [ $? -eq 1 ]; then
        bool=true
      fi
    fi
  fi
done
if $bool; then
  exit 1
else
  echo "No shellcheck errors found."
fi

exit 0
