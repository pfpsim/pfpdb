#!/bin/bash

# Author Lemniscate Snickets 

VirtualEnvironments=( venv-pipwheel venv-piptgz venv-pythoninstall venv-pythondevelop )
Executable=( "pip" "pip" "python" "python" ) 
InstallCommand=( "install" "install" "setup.py" "setup.py" )
InstallTarget=( "*.whl" "pfpdb*.tar.gz" "install" "develop" )
i=0 
for env in "${VirtualEnvironments[@]}"
do
    echo $env
   virtualenv ${env}
   source $env/bin/activate
    ${Executable[${i}]} ${InstallCommand[${i}]} ${InstallTarget[${i}]}
    mkdir temp && cd temp
    #cp ../.tests/* ./ 
    #runtest.sh
    which pfpdb
    pfpdb 
    cd ../ && rm -rf temp
    deactivate
    ((i++))
    echo "-----------Done----------" 
done
