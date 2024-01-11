#!/bin/bash
tree=$1
shot=$2
path=$3
DEBUG_DEVICES=4
mdstcl <<EOF
set tree $tree /shot=$shot
do/meth $path start_stream
type "all done"
exit
EOF
exit 0
