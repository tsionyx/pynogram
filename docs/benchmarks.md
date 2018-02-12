### Benchmark on complex puzzles (remove `2>/dev/null` to see the picture)

```
# use redirection tricks to swap outputs to grep only logs, not the picture
# https://stackoverflow.com/a/2381643/1177288

# http://webpbn.com/pbnsolve.html
for i in 1611 1694 6739 4645 2040 2712 6574 8098 2556; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    time python -m pynogram --pbn $i --draw-final -v 3>&- 3>&1 1>&2 2>&3 |
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

| Name      | Fast CPU, sec | Slow CPU, sec | Contradiction rounds | Solution rate, % |
|-----------|--------------:|--------------:|:--------------------:|-----------------:|
|-- webpbn.com --                                                                     |
| 1611      | 1.33          | 2.06          | 1                    | 100              |
| 1694      | 5.69          | 8.92          | 2                    | 100              |
| **6739**  | 7.83          | 12.81         | 7                    | **98.56**        |
| 4645      | 8.74          | 14.37         | 1                    | 100              |
| 2040      | 8.37          | 13.39         | 3                    | 100              |
| **2712**  | 25.13         | 39.42         | 5                    | **54.78**        |
| **6574**  | 4.10          | 7.46          | 6                    | **29.6**         |
| **8098**  | 1.24          | 1.95          | 2                    | **0**            |
| **2556**  | 3.90          | 6.20          | 3                    | **92.72**        |
|-- Local --                                                                          |
| [football](../pynogram/examples/football.txt) | 0.43  | 0.56  | 1         | 100     |
| [einstein](../pynogram/examples/einstein.txt) | 0.96  | 1.49  | 0         | 100     |
| [MLP](../pynogram/examples/MLP.txt)           | 23.31 | 39.29 | 2         | 100     |



### Colored puzzles

```
for i in 11360 12924 13951 15711 2014 2021 2518 3408 5353 6098 7598 7959 8364 10266 10295 11059 11443 11924 12987 13932 13983 14040 14442 14691 14913 14918 15082 15233 15370; do
    echo "Solving PBN's puzzle #$i (http://webpbn.com/$i) ..."
    /usr/bin/time -f 'Total: %U' python -m pynogram --pbn ${i} --draw-final -v 3>&- 2>/dev/null 3>&1 1>&2 2>&3 |
    grep -iP 'contradiction|Total'
    echo
done
```

| #         | Contradiction rounds | Solution rate, % | Solutions found |
|-----------|:--------------------:|-----------------:|----------------:|
| 11360     |   1                  |
| 12924     |   1                  |
| 13951     |   1                  |
| **15711** |   2                  | 0.872
| **2014**  |   2                  | 0.996
| 2021      |   1                  |                  | 1
| 2518      |   1                  |                  | 1
| 3408      |   1                  |
| **5353**  |   2                  | 0.9833           | 80
| 6098      |   1                  |
| **7598**  |   2                  | 0.9020
| 7959      |   1                  |
| 8364      |   1                  |
| **10266** |   2                  | 0.872
| **10295** |   3                  | 0.9873
| **11059** |   2                  | 0.98
| **11443** |   2                  | 0.7867           | 16
| 11924     |   1                  |
| 12987     |   1                  |
| 13932     |   1                  |                  | 1
| 13983     |   1                  |
| 14040     |   1                  |                  | 1
| 14442     |   1                  |
| **14691** |   2                  | 0.992            | 16
| 14913     |   1                  |                  | 1
| 14918     |   1                  |                  | 1
| 15082     |   1                  |                  | 1
| **15233** |   2                  | 0.9943
| 15370     |   1                  |                  | 1
