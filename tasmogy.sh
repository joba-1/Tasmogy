#!/bin/bash
. ~/.profile
conda activate tasmogy
python ~/bin/tasmogy.py $1
