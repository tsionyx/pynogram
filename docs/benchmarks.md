### Benchmark on complex puzzles (remove `>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    wget -qO- "http://webpbn.com/XMLpuz.cgi?id=$i" > ${i}.xml
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pynogram --local-pbn $i.xml --timeout=1800 --max-solutions=2 --draw-final -v >/dev/null
    rm -f ${i}.xml
done

for i in football einstein MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pynogram --board $i --draw-final -v >/dev/null
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v6 @ 3.80GHz_)
and slightly slower one (_Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz_) CPUs:

| Name      | Fast CPU, sec | Slow CPU, sec | Contradictions found | Solution rate, % | Solutions found | Search depth |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|----------------:|-------------:|
|-- webpbn.com --
| **1611**  | 1.18          | 1.93          | 18                   | 100              | 1
| **1694**  | 1.45          | 2.37          | 99                   | 100              | 1
| **6739**  | 1.69          | 2.70          | 95                   | 98.5625          | 2               | 1
| **4645**  | 2.37          | 4.05          | 33                   | 100              | 1
| **2040**  | 2.08          | 3.27          | 204                  | 100              | 1
| **2712**  | 50            | 113           | 157                  | 54.78 -> 55.05   | 2               | 7
| **6574**  | 78            | 121           | 46                   | 29.6 -> 100      | 1               | 8
| **8098**  | 245           | 389           | 0                    | 0 -> 100         | 1               | 8
| **2556**  | 99            | 169           | 8                    | 92.72 -> 94.50   | 3               | 11
|-- Local --
| [football](../pynogram/examples/football.txt) | 0.70  | 1.10  | 6    | 100          | 1
| [einstein](../pynogram/examples/einstein.txt) | 0.95  | 1.34  | 0    | 100          | 1
| [MLP](../pynogram/examples/MLP.txt)           | 3.43  | 5.54  | 429  | 100          | 1



## Long-solved board (more than 5 minutes, the first 35000 of webpbn's puzzles):

```
$ bash tests/bench.sh {1..35000} 2>&1 >> bench.log &
# and wait for several hours...

$ while read t
  do
    id=$(grep -P ${t} ${log_file} -A2 | grep -oP '#\K(\d+)' | awk '{print $1-1}')
    echo "$id: $t"
  done < <(grep -oP 'Total: \K(.+)' bench.log | sort -gr | awk '$1 > 300')
```

### PyPy (more than 35 seconds)

| #         |  Solution rate, % | Time, sec | Solutions found | Search depth | Board size      | Use equivalent BNW |
|-----------|:-----------------:|----------:|----------------:|-------------:|-----------------|--------------------|
| -- black and white:
| **2556**  | 92.72 -> 94.50    | 108       | 3               | 11           | 45x65 -> 21x17
| **2712**  | 54.78 -> 55.05    | 50        | 2               | 7            | 47x47 -> 41x43
| **6574**  | 29.6 -> 100       | 79        | 1               | 8            | 25x25
| 7290      | 56.60 -> 57.16    | 35        | 2               | 8            | 50x50 -> 37x41
| **8098**  | 0 -> 100          | 271       | 1               | 8            | 19x19
| **9892**  | 33.30 -> 33.35    | >3600     | 0               | 17           | 40x50 -> 37x50
| **12548** | 18.56             | >3600     | 0               | 15           | 40x47 -> 36x43
| 13480     | 12.68             | >3600     | 0               | 21           | 44x43 -> 42x43
| 16900     | 48.06 -> 48.86    | >3600     | 0               | 12           | 80x56 -> 71x56
| **18297** | 13.49 -> 14.15    | 248       | 2               | 8            | 42x36
| **22336** | 42.68 -> 42.72    | >3600     | 0               | 6            | 59x99 -> 58x94
| 25385     | 26.56             | >3600     | 0               | 19           | 50x50 -> 49x48
| 25588     | 35.16             | >3600     | 0               | 15           | 50x50 -> 41x44
| 25820     | 5.26 -> 5.39      | >3600     | 0               | 13           | 75x71
| 26520     | 8.36              | >3600     | 0               | 30           | 60x60 -> 58x57
| 27157     | 42.87 -> 44.80    | 42        | 2               | 4            | 50x30 -> 39x30
| 27174     | 20.28 -> 100      | 1267      | 1               | 5            | 45x55
| 30509     | 0                 | 307       | 2               | 97           | 99x99
| 30532     | 21.44 -> 38.72    | 63        | 2               | 28           | 50x50 -> 46x46
| 30654     | 0                 | 85        | 3               | 432          | 50x50
| -- colored:
| **672**   | 76.38 -> 76.39    | >3600     | 0               | 63           | 52x52 -> 51x51  | Y
| **672**   | ^^^               | ^^^       | ^^^             | 44           | ^^^             | N
| **2498**  | 90.68             | 906       | 2               | 20           | 45x75 -> 41x59
| 3085      | 88.91 -> 88.98    | >3600     | 0               | 10           | 55x40 -> 50x33  | Y
| 3085      | ^^^               | ^^^       | ^^^             | 11           | ^^^             | N
| 3114      | 81.61             | 24        | 2               | 15           | 60x50 -> 57x44  | Y
| 3114      | ^^^               | 12        | ^^^             | ^^^          | ^^^             | N
| **3149**  | 78.62             | >3600     | 0               | 28           | 40x40 -> 32x32
| **3620**  | 85.81             | >3600     | 0               | 19           | 20x20
| 7541      | 97.13             | 241       | 2               | 22           | 99x99 -> 77x55
| 9786      | 63.35             | >3600     | 0               | 8            | 40x50 -> 38x50  | Y
| 9786      | ^^^               | ^^^       | ^^^             | 9            | ^^^             | N
| 10585     | 85.85             | >3600     | 0               | 16           | 50x50 -> 41x46  | Y
| 10585     | ^^^               | ^^^       | ^^^             | 17           | ^^^             | N
| 11058     | 92.89             | 101       | 2               | 13           | 45x35 -> 39x35
| 12831     | 90.75             | >3600     | 0               | 14           | 50x50 -> 37x33
| 16552     | 96.40             | 4         | 4               | 23           | 50x50 -> 46x46  | Y
| 16552     | ^^^               | >3600)    | 0               | 15           | ^^^             | N
| 16820     | 88.91             | 353       | 3               | 20           | 62x64 -> 33x43  | Y
| 16820     | ^^^               | 5         | 2               | ^^^          | ^^^             | N
| 16838     | 68.92 -> 69.08    | >3600     | 0               | 25           | 64x86 -> 38x59
| 16878     | 86.22             | 17        | 2               | 17           | 72x70 -> 53x66  | Y
| 16878     | ^^^               | >3600     | 0               | 14           | ^^^             | N
| 16905     | 96.69             | 25        | 2               | 1            | 79x68 -> 61x62  | Y
| 16905     | ^^^               | 23        | ^^^             | 0            | ^^^             | N
| 17045     | 95.96 -> 96.01    | >3600     | 0               | 12           | 55x55 -> 38x33
| 18290     | 37.5              | >3600     | 0               | 21           | 20x20
| 25158     | 85.70 -> 85.83    | >3600     | 0               | 7            | 35x50           | Y
| 25158     | ^^^               | ^^^       | ^^^             | 10           | ^^^             | N
| 25540     | 83.16             | >3600     | 0               | 13           | 50x50 -> 39x36
| 26810     | 79.28             | >3600     | 0               | 21           | 60x50 -> 54x41
| 29436     | 84.40 -> 84.41    | >3600     | 0               | 9            | 71x71 -> 67x67  | Y
| 29436     | ^^^               | ^^^       | ^^^             | 11           | ^^^             | N
| 29826     | 86.72 -> 86.80    | 36        | 2               | 16           | 60x60 -> 60x47
| 30640     | 96.79 -> 96.80    | >3600     | 0               | 14           | 69x60 -> 58x51  | Y
| 30640     | ^^^               | ^^^       | ^^^             | 13           | ^^^             | N
| 31114     | 18.50             | >3600     | 0               | 34           | 20x20


**Bold** puzzles are from http://webpbn.com/survey/ (_italic_ puzzles are mentioned there too).

The arrow (->) in 'Solution rate' shows changes of full solution during the backtracking phase.

The arrow (->) in 'Board size' shows that the board was reduced to the given size before the backtracking phase.
