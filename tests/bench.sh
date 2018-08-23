#!/bin/bash -e

# nohup bash tests/bench.sh {1..35000} 2>&1 >> bench.log & tail -f bench.log

mkdir -p solutions

echo "Start at $(date)"
for i in $@; do
    wget -qO- "http://webpbn.com/XMLpuz.cgi?id=$i" > ${i}.xml
    if cat ${i}.xml | head -1 | grep -q '<?xml'; then
        echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
        /usr/bin/time -f 'Total: %U' python -m pynogram --local-pbn ${i}.xml --draw-final -v --timeout=3600 --max-solutions=2 2>&1 1>solutions/${i}
    else
        echo "Failed to retrieve puzzle #$i" >&2
    fi
    rm -f ${i}.xml
    echo
done

echo "End at $(date)"


function grep_puzzle_number() {
    grep -oP '#\K(\d+)' | awk '{print $1-1}'
}

function stats() {
  log_file=$1

  # number of unsolved
  grep -A5 'not solved full' ${log_file} | grep_puzzle_number | wc -l
  # 161

  # the worst unsolved scores
  grep 'not solved full' ${log_file} | awk '{print $17}' | sort -n | head -n5
  # 0.0000
  # 0.0000
  # 0.0000
  # 0.0005
  # 0.0069


  # check for exceptions
  grep -A7 File ${log_file} | grep_puzzle_number

  # the puzzles that solves too long (more than 20 seconds)
  while read t
  do
    id=$(grep -P ${t} ${log_file} -A2 | grep_puzzle_number)
    echo "$id: $t"
  done < <(grep -oP 'Total: \K(.+)' ${log_file} | sort -gr | awk '$1 > 20')
}
