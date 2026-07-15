CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra -Isrc

LDLIBS =
ifeq ($(OS),Windows_NT)
	LDLIBS += -lws2_32
endif

.PHONY: all clean

all: sender receiver

sender: src/sender.cpp src/proto.h src/env.h src/platform.h
	$(CXX) $(CXXFLAGS) -o sender src/sender.cpp $(LDLIBS)

receiver: src/receiver.cpp src/proto.h src/env.h src/platform.h
	$(CXX) $(CXXFLAGS) -o receiver src/receiver.cpp $(LDLIBS)

clean:
	rm -f sender receiver sender.exe receiver.exe
