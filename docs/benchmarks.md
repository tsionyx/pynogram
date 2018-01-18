### Benchmark on complex puzzles (remove `2>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643/1177288

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pynogram --pbn $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done

for i in football einstein MLP; do
    echo "Solving local puzzle $i ..."
    time python -m pynogram --board $i --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
        grep -i contradict
done
```

Currently it gives these numbers on the fast (_Intel(R) Xeon(R) CPU E3-1275 v5 @ 3.60GHz_)
and slower (_Intel(R) Core(TM) i5 CPU  M 560  @ 2.67GHz_) CPUs:

| Name      | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
|-- webpbn.com --                                                                     |
| 1611      | 1.21          | 2.15          | 1                    | 100              |
| 1694      | 8.91          | 16.20         | 5                    | 100              |
| **6739**  | 7.62          | 13.96         | 7                    | **98.56**        |
| 4645      | 6.34          | 12.01         | 1                    | 100              |
| 2040      | 36.04         | 67.02         | 4                    | 100              |
| **2712**  | 34.02         | 61.39         | 6                    | **54.78**        |
| **6574**  | 3.82          | 6.84          | 7                    | **29.6**         |
| **8098**  | 0.86          | 1.32          | 1                    | **0**            |
| **2556**  | 1.83          | 3.12          | 3                    | **92.72**        |
|-- Local --                                                                          |
| [football](../pynogram/examples/football.txt) | 0.63  | 1.04  | 1         | 100              |
| [einstein](../pynogram/examples/einstein.txt) | 0.86  | 1.58  | 0         | 100              |
| [MLP](../pynogram/examples/MLP.txt)           | 18.90 | 35.08 | 3         | 100              |



### Colored puzzles

```
for i in 11360 12924 13951 15711 2014 2021 2518 3408 5353 6098 7598 7959 8364 10266 10295 11059 11443 11924 12987 13932 13983 14040 14442 14691 14913 14918 15082 15233 15370; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    /usr/bin/time -f 'Total: %U' python -m pynogram --pbn ${i} --draw-final 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
    grep -iP 'contradiction|Total'
    echo
done
```

| #         | Contradiction rounds | Solution rate, % | Solutions found |
|-----------|:--------------------:|-----------------:|----------------:|
| 11360     |   1                  |                  | 6
| 12924     |   1                  |                  | 1
| 13951     |   1                  |                  |
| **15711** |   6                  | 0.872
| **2014**  |   1                  | 0.996
| 2021      |   1                  |                  | 1
| 2518      |   2                  |                  |
| 3408      |   3                  |
| **5353**  |   1                  | 0.9833           | 80
| 6098      |   2                  |
| **7598**  |   6                  | 0.9020
| 7959      |   1                  |
| 8364      |   1                  |                  | 1
| **10266** |   6                  | 0.872
| **10295** |   13                 | 0.9873
| **11059** |   5                  | 0.98
| **11443** |   4                  | 0.7867           | 16
| 11924     |   1                  |
| 12987     |   1                  |
| 13932     |   2                  |                  | 1
| 13983     |   3                  |
| 14040     |   1                  |                  | 1
| 14442     |   1                  |                  | 1
| **14691** |   6                  | 0.992            | 16
| 14913     |   1                  |                  | 1
| 14918     |   1                  |                  | 1
| 15082     |   1                  |                  | 1
| **15233** |   5                  | 0.9943
| 15370     |   1                  |                  | 1
