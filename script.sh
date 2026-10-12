#/bin/bash

primes=(2 3 5 7 11 13 17 19 23 29 31 37 41 43 47 53 59 61 67) #71 73 79 83 89 97)
# primes=(2 3 5 7);

for index in {0..18}; do
  for (( i = $index+1; i <= 18; i++ )); do
    python3 test.py -g 1 -s 1 -d 0 -f 1 -p ${primes[$index]} -q ${primes[$i]};
  done
done

wait;

python3 merge_dicts.py
