CC := gcc
SRCD := src
TSTD := tests
BLDD := build
BIND := bin
INCD := include

EXEC := pbf

MAIN  := $(BLDD)/main.o

ALL_SRCF := $(shell find $(SRCD) -type f -name *.c)
ALL_OBJF := $(patsubst $(SRCD)/%,$(BLDD)/%,$(ALL_SRCF:.c=.o))
ALL_FUNCF := $(filter-out $(MAIN) $(AUX), $(ALL_OBJF))

INC := -I $(INCD)

CFLAGS := -fcommon -Wall -Wno-unused-function -MMD -std=gnu11 -Wno-format

LIBS := -lz

CFLAGS += $(STD)

.PHONY: clean all setup debug

all: setup $(BIND)/$(EXEC) $(BIND)/$(TEST_EXEC)

setup: $(BIND) $(BLDD)
$(BIND):
	mkdir -p $(BIND)
$(BLDD):
	mkdir -p $(BLDD)

$(BIND)/$(EXEC): $(MAIN) $(ALL_FUNCF)
	$(CC) $(CFLAGS) $(INC) $(MAIN) $(ALL_FUNCF) -o $@ $(LIBS)


$(BLDD)/%.o: $(SRCD)/%.c
	$(CC) $(CFLAGS) $(INC) -c -o $@ $<

clean:
	rm -rf $(BLDD) $(BIND)

.PRECIOUS: $(BLDD)/*.d
-include $(BLDD)/*.d
