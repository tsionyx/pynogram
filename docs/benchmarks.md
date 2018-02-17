### Benchmark on complex puzzles (remove `2>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643/1177288

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pynogram --pbn $i --draw-final -v 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done

for i in football einstein MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pynogram --board $i --draw-final -v 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| Name      | Fast CPU, sec | Slow CPU, sec | Contradiction rounds (found) | Solution rate, % |
|-----------|--------------:|--------------:|:----------------------------:|-----------------:|
|-- webpbn.com --                                                                             |
| 1611      | 1.74          | 2.34          | 1 (18)                       | 100              |
| 1694      | 2.14          | 3.93          | 1 (99)                       | 100              |
| **6739**  | 2.90          | 4.45          | 3 (95, 0, 0)                 | **98.5625**      |
| 4645      | 5.16          | 9.14          | 1 (33)                       | 100              |
| 2040      | 6.20          | 11.49         | 1 (204)                      | 100              |
| **2712**  | 10.26         | 19.48         | 5 (149, 3, 0, 5, 0)          | **54.7759**      |
| **6574**  | 1.88          | 3.09          | 5 (44, 1, 0, 1, 0)           | **29.6**         |
| **8098**  | 0.62          | 1.02          | 2 (0, 0)                     | **0**            |
| **2556**  | 1.80          | 2.54          | 3 (8, 0, 0)                  | **92.7179**      |
|-- Local --                                                                                  |
| [football](../pynogram/examples/football.txt) | 0.41  | 0.52  | 1 (6)    | 100              |
| [einstein](../pynogram/examples/einstein.txt) | 1.42  | 2.04  | 0        | 100              |
| [MLP](../pynogram/examples/MLP.txt)           | 11.13 | 20.11 | 1 (429)  | 100              |



### Colored puzzles

```
for i in 11360 12924 13951 15711 2014 2021 2518 3408 5353 6098 7598 7959 8364 10266 10295 11059 11443 11924 12987 13932 13983 14040 14442 14691 14913 14918 15082 15233 15370; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    /usr/bin/time -f 'Total: %U' python -m pynogram --pbn ${i} --draw-final -v 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
    grep -iP 'contradiction|Total'
    echo
done
```

| #         | Contradiction rounds (found) | Solution rate, % | Solutions found |
|-----------|:----------------------------:|-----------------:|----------------:|
| 11360     |   1 (6)                      |
| 12924     |   1 (1)                      |
| 13951     |   1 (1)                      |
| **15711** |   2 (0, 0)                   | 0.84
| **2014**  |   2 (0, 0)                   | 0.995
| 2021      |   1 (1)                      |                  | 1
| 2518      |   1 (12)                     |                  | 1
| 3408      |   1 (2)                      |
| **5353**  |   2 (0, 0)                   | 0.966667         | 80
| 6098      |   1 (1)                      |
| **7598**  |   2 (0, 0)                   | 0.836667
| 7959      |   1 (1)                      |
| 8364      |   1 (1)                      |
| **10266** |   2 (0, 0)                   | 0.84
| **10295** |   3 (4, 0, 0)                | 0.984167
| **11059** |   2 (0, 0)                   | 0.96
| **11443** |   2 (0, 0)                   | 0.68             | 16
| 11924     |   1 (1)                      |
| 12987     |   1 (1)                      |
| 13932     |   1 (1)                      |                  | 1
| 13983     |   1 (1)                      |
| 14040     |   1 (1)                      |                  | 1
| 14442     |   1 (1)                      |
| **14691** |   2 (0, 0)                   | 0.986667         | 16
| 14913     |   1 (2)                      |                  | 1
| 14918     |   1 (1)                      |                  | 1
| 15082     |   1 (1)                      |                  | 1
| **15233** |   2 (0, 0)                   | 0.988571
| 15370     |   1 (1)                      |                  | 1
