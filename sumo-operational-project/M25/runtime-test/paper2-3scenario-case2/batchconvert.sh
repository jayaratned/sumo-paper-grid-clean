#!/usr/bin/env bash

for file in e1/*.xml
do
    python -m sumo.tools.xml.xml2csv "$file"
done
