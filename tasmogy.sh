#!/bin/bash
. ~/.bashrc
conda activate tasmogy
exec python -u ~/bin/tasmogy.py $@
