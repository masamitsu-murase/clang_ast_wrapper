
ruby test/download.rb python python.exe
if ERRORLEVEL 1 (
    echo download python error
    exit /b 1
)

ruby test/download.rb libclang libclang.dll
if ERRORLEVEL 1 (
    echo download libclang error
    exit /b 1
)

.\python.exe -m unittest discover
if ERRORLEVEL 1 (
    exit /b 1
)

exit /b 0
