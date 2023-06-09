#!/bin/bash


source venv/bin/activate

for f in `ls -1 access.log*`; do
  python3 main_georhena.py $f gh_processed_logs.log
done
