#!/bin/bash

for f in `ls -1 *.d2`; do
  d2 $f ${f%.d2}.svg
done
