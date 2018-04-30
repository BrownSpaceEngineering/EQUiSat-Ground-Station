# Makefile for Cross Interleaved Reed Solomon encoder/decoder
#
# (c) Henry Minsky, Universal Access 1991-1996
#

RANLIB = ranlib
AR = ar


VERSION = 1.0
DIRNAME= rscode-$(VERSION)


CC = gcc
# OPTIMIZE_FLAGS = -O69
DEBUG_FLAGS = -g
CFLAGS = -Wall -Wstrict-prototypes  $(OPTIMIZE_FLAGS) $(DEBUG_FLAGS) -I..
LDFLAGS = -fPIC $(OPTIMIZE_FLAGS) $(DEBUG_FLAGS) -L. -lecc 

LIB_CSRC = rs.c galois.c berlekamp.c crcgen.c 
LIB_HSRC = ecc.h
LIB_OBJS = rscode1.3/rs.o rscode1.3/galois.o rscode1.3/berlekamp.o rscode1.3/crcgen.o 

TARGET_LIB = libecc.a
TEST_PROGS =rsdecode rsencode

TARGETS = $(TARGET_LIB) $(TEST_PROGS)

all: $(TARGETS)

$(TARGET_LIB): $(LIB_OBJS)
	$(RM) $@
	$(AR) cq $@ $(LIB_OBJS) -fPIC
	if [ "$(RANLIB)" ]; then $(RANLIB) $@; fi

rsdecode: rsdecode.o rscode1.3/galois.o rscode1.3/berlekamp.o rscode1.3/crcgen.o rscode1.3/rs.o
	gcc $(CFLAGS) -o rsdecode rsdecode.o $(LDFLAGS)

rsencode: rsencode.o rscode1.3/galois.o rscode1.3/berlekamp.o rscode1.3/crcgen.o rscode1.3/rs.o
	gcc $(CFLAGS) -o rsencode rsencode.o $(LDFLAGS) 
clean:
	rm -f *.o example libecc.a
	rm -f *~

dist:
	(cd ..; tar -cvf rscode-$(VERSION).tar $(DIRNAME))

depend:
	makedepend $(SRCS)

# DO NOT DELETE THIS LINE -- make depend depends on it.

