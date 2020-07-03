#!/bin/bash

python ./train.py \
  --model ResNetSE34L \
  --encoder SAP \
  --trainfunc amsoftmax \
  --optimizer adam \
  --save_path data/exp1 \
  --batch_size 200 \
  --max_frames 200 \
  --scale 30 \
  --margin 0.3 \
  --train_list /home/joon/voxceleb/train_list.txt \
  --test_list /home/joon/voxceleb/test_list.txt \
  --train_path /home/joon/voxceleb/voxceleb2 \
  --test_path /home/joon/voxceleb/voxceleb1
