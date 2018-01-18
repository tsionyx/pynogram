#!/bin/bash

# nohup bash tests/bench.sh {1..2000} 2>&1 >> bench.log & tail -f bench.log

for i in $@; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    /usr/bin/time -f 'Total: %U' python -m pynogram --pbn ${i} --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
    grep -iP 'contradiction|Total'
    echo
done


function stats() {
  log_file=$1

  # number of unsolved
  grep -A3 'not solved full' ${log_file} | grep -oP '#\K(\d+)' | awk '{print $1-1}' | wc -l
  # 161

  # the worst unsolved scores
  grep 'not solved full' ${log_file} | awk '{print $17}' | sort -n | head -n5
  # 0.0000
  # 0.0000
  # 0.0000
  # 0.0005
  # 0.0069


  # no exceptions found!!!
  grep File ${log_file} | sort | uniq -c | awk '{print $1,$4,$5,$7}'
  grep -A5 'line 73' ${log_file} | grep -oP '#\K(\d+)' | awk '{print $1-1}'
}
