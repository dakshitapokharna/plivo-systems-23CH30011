// Run parameters the harness passes to both our processes via environment
// variables. T0/DURATION_S are assumed to be unix epoch seconds (may have
// a fractional part) since that's what a Python time.time()-based harness
// naturally emits. If the real handout's common.py uses a different
// convention (e.g. integer milliseconds), this is the one place to fix it.
#pragma once

#include <cstdlib>
#include <stdexcept>
#include <string>

namespace proto {

struct Env {
    double t0 = 0;
    double duration_s = 0;
    int delay_ms = 0;

    // A couple seconds past nominal end - the harness kills us anyway,
    // this just avoids a lingering process during local testing.
    double end_time_epoch() const { return t0 + duration_s + 2.0; }
};

inline double parse_double_env(const char* name) {
    const char* v = std::getenv(name);
    if (!v || !*v) throw std::runtime_error(std::string(name) + " not set");
    char* end = nullptr;
    double d = std::strtod(v, &end);
    if (end == v) throw std::runtime_error(std::string(name) + "=\"" + v + "\": not a number");
    return d;
}

inline Env load_env() {
    Env e;
    e.t0 = parse_double_env("T0");
    e.duration_s = parse_double_env("DURATION_S");
    e.delay_ms = static_cast<int>(parse_double_env("DELAY_MS"));
    return e;
}

} // namespace proto
