#!/bin/bash

root_dir=`dirname $0`

nohup python3 $root_dir/run_stockopr_module.py toolkit/digit_clock.py > /dev/null 2>&1 &