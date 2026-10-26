CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror

test: test_keys
	./test_keys

test_keys: test_keys.c ../src/keys.c ../src/keys.h
	$(CC) $(CFLAGS) -I../src -o $@ test_keys.c ../src/keys.c -lm

clean:
	rm -f test_keys

.PHONY: test clean
