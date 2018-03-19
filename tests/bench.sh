#!/bin/bash -e

# nohup bash tests/bench.sh {1..23000} 2>&1 >> bench.log & tail -f bench.log

mkdir -p solutions

echo "Start at $(date)"
for i in $@; do
    if wget -qO- "http://webpbn.com/XMLpuz.cgi?id=$i" | head -1 | grep -q '<?xml'; then
        echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
        /usr/bin/time -f 'Total: %U' python -m pynogram --pbn ${i} --draw-final -v --timeout=3600 --max-solutions=2 2>&1 1>solutions/${i}
    else
        echo "Failed to get puzzle #$i" >&2
    fi
    echo
done

echo "End at $(date)"

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


  # check for exceptions
  grep File ${log_file} | sort | uniq -c | awk '{print $1,$4,$5,$7}'

  # the puzzles that solves too long (more than 5 minutes)
  while read t
  do
    id=$(grep -P ${t} ${log_file} -A2 | grep -oP '#\K(\d+)' | awk '{print $1-1}')
    echo "$id: $t"
  done < <(grep -oP 'Total: \K(.+)' ${log_file} | sort -gr | awk '$1 > 300')
}
