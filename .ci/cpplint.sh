#!/bin/sh

#checks="*,-llvm-header-guard,-hicpp-no-assembler,-google-readability-todo,-modernize-use-trailing-return-type,-cppcoreguidelines-macro-usage,-misc-unused-parameters,-cppcoreguidelines-pro-bounds-pointer-arithmetic"
checks="*,-llvm-header-guard,-google-readability-todo"

echo "Doing cppllint..."
bool=false
# explicitly set IFS to contain only a line feed
IFS='
'
filelist="$(find . -type f ! -name "$(printf "*\n*")")"
for file in $filelist; do
	if echo "$file" | grep -q -E "(.*\.cpp$|.*\.hpp$|.*\.hxx$)" ; then
		# check if parameter 1 contains a file
		if [ -f "$1" ]; then
			file="$1"
		fi
		# check if parameter 2 def
		if [ "$2" ]; then
			checks="$2"
		fi
		#Extra check missing dependencs due to clang-tidy doesn't toggel exit code.
		clang_tidy_lib_check="$(clang-tidy -quiet -warnings-as-errors='*' -header-filter='.*' -checks="$checks" "$file" -extra-arg=-std=c++17 -extra-arg-before=-std=c++17 -- 2>&1)"
		for tidy_line in $clang_tidy_lib_check; do
			echo "$tidy_line" | grep -q -v -E "^Error while processing*"
			if [ $? -eq 1 ]; then
				bool=true
			fi
			echo "$tidy_line" | grep -q -v -E ".* error: .*"
			if [ $? -eq 1 ]; then
				bool=true
			fi
			echo "$tidy_line"
		done
		# exit by overwritten file val
		if [ -f "$1" ]; then
			exit 0
		fi
	fi
done
if $bool; then
	exit 1
else
	echo "No clang-tidy errors found."
fi

exit 0
