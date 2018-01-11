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
| [football](../examples/football.txt) | 0.63  | 1.04  | 1         | 100              |
| [einstein](../examples/einstein.txt) | 0.86  | 1.58  | 0         | 100              |
| [MLP](../examples/MLP.txt)           | 18.90 | 35.08 | 3         | 100              |
