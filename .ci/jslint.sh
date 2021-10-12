#!/bin/sh

echo "Doing jslint..."
bool=false
# explicitly set IFS to contain only a line feed
IFS='
'
filelist="$(find . -type f ! -name "$(printf "*\n*")")"
for line in $filelist; do
  if echo "$line" | grep -E -q ".*\.\/.*\.js$" ; then
    if ! grep -Eq "$line" ".ci/js_accepted"; then
      if ! jslint --terse --browser "$line"; then
        bool=true
      fi
    fi
  fi
done
if $bool; then
  exit 1
else
  echo "No jslint errors found."
fi

exit 0
